import json
import time
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from ddgs import DDGS


load_dotenv()  
API_KEY = os.getenv("API_KEY", "sk-txdaajjckmyvdofjxfvxdbujixgjoyitllxamzsqhatnjpgr")

BASE_URL = os.getenv("BASE_URL", "https://api.siliconflow.cn/v1").strip()
MODEL = os.getenv("MODEL", "zai-org/GLM-4.6")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# ---------- 工具：网页搜索 ----------
def web_search(query: str, max_results: int = 8) -> str:
    """返回拼接好的搜索摘要（供模型阅读）。"""
    print(f"[DEBUG] 执行搜索：{query}")
    try:
        results = list(DDGS(proxy=None).text(query, max_results=max_results))
    except Exception as e:
        print("[ERROR] 搜索工具执行失败：", e)
        return "（搜索工具执行失败）"

    print(f"[DEBUG] 抓到 {len(results)} 条")
    lines = []
    for idx, r in enumerate(results, start=1):
        title = r.get("title") or ""
        href = r.get("href") or ""
        body = r.get("body") or ""
        snippet = body.strip().replace("\n", " ")
        lines.append(f"[{idx}] {title} | {href}\n{snippet[:300]}...")
        print(f"[DEBUG-{idx}] {title} | {snippet[:80]}...")
    if not lines:
        return "（暂无搜索结果）"
    return "\n\n".join(lines)


# ---------- LLM 调用封装（含稳健的 usage 提取与调试记录） ----------
def call_llm(messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            stream=False
        )
    except Exception as e:
       
        print("[ERROR] LLM 调用失败：", repr(e))
        raise

    latency = round(time.perf_counter() - start, 3)

   
    content = ""
    try:
      
        if hasattr(res, "choices"):
            content = res.choices[0].message.content
        elif isinstance(res, dict):
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            content = str(res)
    except Exception:
        try:
            # fallback to dict-like
            d = res.to_dict() if hasattr(res, "to_dict") else dict(res)
            content = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = str(res)

   
    usage = {}
    try:
        if hasattr(res, "usage") and getattr(res, "usage") is not None:
            usage = getattr(res, "usage")
        elif hasattr(res, "to_dict"):
            d = res.to_dict()
            usage = d.get("usage", {}) or {}
        elif isinstance(res, dict):
            usage = res.get("usage", {}) or {}
    except Exception:
        usage = {}

   
    def _get_int_field(d: Any, *keys):
        if not d:
            return None
        for k in keys:
            try:
                v = d.get(k)
            except Exception:
                try:
                    v = getattr(d, k)
                except Exception:
                    v = None
            if v is not None:
                try:
                    return int(v)
                except Exception:
                    try:
                        return int(float(v))
                    except Exception:
                        return None
        return None

    prompt_tokens = _get_int_field(usage, "prompt_tokens", "promptToken", "promptTokens")
    completion_tokens = _get_int_field(usage, "completion_tokens", "completionToken", "completionTokens")
    total_tokens = _get_int_field(usage, "total_tokens", "totalToken", "totalTokens")

   
    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        try:
            dbg = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "latency": latency,
                "model": MODEL,
                "message_sample": content[:800],
                "res_type": str(type(res)),
            }
           
            try:
                if hasattr(res, "to_dict"):
                    dbg["res_keys"] = list(res.to_dict().keys())
                elif isinstance(res, dict):
                    dbg["res_keys"] = list(res.keys())
            except Exception:
                pass
            with open("debug_responses.jsonl", "a", encoding="utf-8") as fdbg:
                fdbg.write(json.dumps(dbg, ensure_ascii=False) + "\n")
            print("[DEBUG] 未找到 usage 字段（已写入 debug_responses.jsonl 以便排查）")
        except Exception as e:
            print("[WARN] 写入 debug_responses.jsonl 失败：", e)

    return {
        "content": content,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency": latency,
        "raw": res, 
    }


# ---------- 解析模型指令 ----------
def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    尝试从文本中提取第一对花括号内的 JSON 并解析。
    若失败返回 None。会做轻微修复（单引号->双引号，去掉末尾逗号）。
    """
    if not text or "{" not in text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start:end+1]
    try:
        return json.loads(candidate)
    except Exception:
        # 轻修复后重试
        try:
            candidate2 = candidate.replace("'", '"')
            candidate2 = candidate2.replace(",}", "}")
            candidate2 = candidate2.replace(",]", "]")
            return json.loads(candidate2)
        except Exception:
            return None


# ---------- Agent 主循环（模型主导搜索） ----------
def run_agent_model_driven(user_query: str, max_rounds: int = 10):
    start_ts = time.perf_counter()  
    system = (
        "你是一个能主动发起网页搜索的智能代理。你和外部搜索工具交互的方式如下：\n"
        "当你需要网页信息以继续推理时，请只输出一个 JSON 对象：\n"
        "  {\"action\": \"search\", \"query\": \"要搜索的文本查询\"}\n"
        "当你已经有足够信息并准备给出最终回答时，请只输出一个 JSON 对象：\n"
        "  {\"action\": \"answer\", \"answer\": \"你的完整答案（简洁、清晰）\"}\n"
        "不要输出其它多余文本（但如果输出非严格 JSON，我会尝试从中抽取 JSON）。\n"
        "每次当你指示 action=search，我会运行搜索并把搜索结果作为新的消息回传给你，"
        "你可以基于这些结果继续决定搜索或最终回答。\n"
        "限制：最多进行 `max_rounds` 次搜索（外部会强制），请在必要时优先提出最有价值的查询。"
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"用户问题：{user_query}\n\n请决定下一步（搜索 or 回答）。"}
    ]

    all_searches: List[Dict[str, Any]] = []
    llm_calls: List[Dict[str, Any]] = []

   
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens_backfill = 0

    for round_idx in range(1, max_rounds + 1):
        print(f"\n=== Round {round_idx} (模型决定是否搜索或回答) ===")
        llm_out = call_llm(messages)
        llm_calls.append(llm_out)

     
        pt = llm_out.get("prompt_tokens")
        ct = llm_out.get("completion_tokens")
        tt = llm_out.get("total_tokens")
        if pt is not None and ct is not None:
            try:
                total_prompt_tokens += int(pt)
                total_completion_tokens += int(ct)
            except Exception:
                pass
        elif tt is not None:
            try:
                total_tokens_backfill += int(tt)
            except Exception:
                pass
        else:
            
            print("[DEBUG] 本次 LLM 响应没有可用 usage 信息（查看 debug_responses.jsonl）。")

        print("[LLM output]")
     
        print(llm_out["content"][:1500])

     
        op = extract_json_object(llm_out["content"])
        if not op:
            
            final_answer = llm_out["content"].strip()
            print("[WARN] 未解析到 JSON 操作，直接采用模型输出作为最终答案。")
            save_metrics_and_print(user_query, final_answer, all_searches, llm_calls,
                                   total_prompt_tokens, total_completion_tokens, total_tokens_backfill, start_ts)
            return

        action = (op.get("action") or "").lower()
        if action == "search":
            search_q = op.get("query") or op.get("q") or ""
            if not search_q:
                print("[WARN] model 指示搜索但未提供 query（空 query）。将该响应回写对话并继续。")
                messages.append({"role": "assistant", "content": llm_out["content"]})
                
                if round_idx == max_rounds:
                    final_answer = llm_out["content"]
                    save_metrics_and_print(user_query, final_answer, all_searches, llm_calls,
                                           total_prompt_tokens, total_completion_tokens, total_tokens_backfill, start_ts)
                    return
                continue

          
            search_start = time.perf_counter()
            snippets = web_search(search_q)
            search_latency = round(time.perf_counter() - search_start, 3)
            all_searches.append({"query": search_q, "snippets": snippets, "search_latency": search_latency})
            messages.append({"role": "assistant", "content": llm_out["content"]})
            messages.append({
                "role": "system",
                "content": f"[TOOL:search results for \"{search_q}\" | latency={search_latency}s]\n\n{snippets}"
            })
            continue

        elif action == "answer":
            final_answer = op.get("answer") or op.get("result") or ""
            if not final_answer:
                final_answer = llm_out["content"]
            save_metrics_and_print(user_query, final_answer, all_searches, llm_calls,
                                   total_prompt_tokens, total_completion_tokens, total_tokens_backfill, start_ts)
            return
        else:
          
            print(f"[WARN] 未知 action: '{action}'，将模型响应写回对话并继续。")
            messages.append({"role": "assistant", "content": llm_out["content"]})
            if round_idx == max_rounds:
                final_answer = llm_out["content"]
                save_metrics_and_print(user_query, final_answer, all_searches, llm_calls,
                                       total_prompt_tokens, total_completion_tokens, total_tokens_backfill, start_ts)
                return
            continue

   
    print("[INFO] 达到最大轮数，使用最后一次模型输出作为答案（如果可用）。")
    last = llm_calls[-1]["content"] if llm_calls else "（无响应）"
    save_metrics_and_print(user_query, last, all_searches, llm_calls,
                           total_prompt_tokens, total_completion_tokens, total_tokens_backfill, start_ts)


# ---------- 保存与输出指标（包含序列化清理） ----------
def save_metrics_and_print(query: str, answer: str, searches: List[Dict[str, Any]],
                           llm_calls: List[Dict[str, Any]],
                           total_prompt_tokens: int,
                           total_completion_tokens: int,
                           total_tokens_backfill: int,
                           start_ts: float):
    
    total_seconds = time.perf_counter() - start_ts
    minutes, sec = divmod(int(total_seconds), 60)
    ms = int((total_seconds - int(total_seconds)) * 1000)
    elapsed_str = f"{minutes:02d}:{sec:02d}.{ms:03d}"

  
    sanitized_calls = []
    for c in llm_calls:
        sanitized = {
            "content_sample": (c.get("content") or "")[:800],
            "prompt_tokens": c.get("prompt_tokens"),
            "completion_tokens": c.get("completion_tokens"),
            "total_tokens": c.get("total_tokens"),
            "latency": c.get("latency"),
            "raw_type": str(type(c.get("raw"))) if "raw" in c else None
        }
        sanitized_calls.append(sanitized)

    metrics = {
        "query": query,
        "answer": answer,
        
        "llm_calls_count": len(llm_calls),
        "total_prompt_tokens": total_prompt_tokens if total_prompt_tokens > 0 else None,
        "total_completion_tokens": total_completion_tokens if total_completion_tokens > 0 else None,
        
        "elapsed": elapsed_str,      
    }

    
    try:
        with open("metrics.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    except Exception as e:
        print("[WARN] 写入 metrics.jsonl 失败：", e)

    print("\n----- FINAL ANSWER -----")
    print(answer)
    print("\n----- METRICS -----")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


# ---------- CLI ----------
if __name__ == "__main__":
    q = input("请输入问题：").strip()
    if q:
        run_agent_model_driven(q, max_rounds=10)