"""2026-06-04 全量真实 API 回归执行器。

该脚本复用仓库内已有的真实 CLI 回归能力，但把本次测试的输出路径、报告样式、
增量落盘节奏和少量样本补丁收束到一个独立入口中，避免改动业务实现。
调用方需要关注的关键点：
1. 强制使用项目 .venv 中的解释器执行真实 CLI；
2. 从测试开始即持续刷新 HTML / JSON 报告；
3. 保留每条命令的真实 stdout / stderr、耗时、失败分类和 backend 元数据。
"""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tests.run_third_full_regression as base

REPORT_STEM = "20260604-第1次测试结论"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORT_HTML = DOCS_DIR / f"{REPORT_STEM}.html"
RESULT_JSON = DOCS_DIR / f"{REPORT_STEM}.results.json"
RAW_JSON = DOCS_DIR / f"{REPORT_STEM}.raw.json"
ARTIFACT_DIR = DOCS_DIR / f"{REPORT_STEM}-artifacts"

base.ARTIFACT_DIR = ARTIFACT_DIR
base.RESULT_JSON = RESULT_JSON
base.RAW_JSON = RAW_JSON
base.REPORT_HTML = REPORT_HTML


def ensure_option(tokens: list[str], option_name: str, option_value: str) -> list[str]:
    """确保命令 token 中包含指定 option，避免覆盖矩阵因缺参而失效。

    Args:
        tokens: 原始命令 token 列表。
        option_name: 需要补入的 option 名称。
        option_value: 需要补入的 option 取值。

    Returns:
        处理后的 token 列表。若原列表已包含该 option，则原样返回。
    """

    if option_name in tokens:
        return tokens
    if "--backend" in tokens:
        index = tokens.index("--backend")
        return tokens[:index] + [option_name, option_value] + tokens[index:]
    return tokens + [option_name, option_value]


def build_cases() -> list[dict[str, Any]]:
    """构建本次 2026-06-04 专用回归矩阵。

    这里复用第三次全量回归脚本的样本集，仅对当前源码校验发现缺失的业务参数做
    最小修正，从而保证覆盖矩阵与当前 CLI 结构一致。

    Returns:
        可以直接传给基础回归执行器的用例列表。
    """

    cases = base.build_cases()
    for case in cases:
        if case["path"] == "stock price latest" and case["backend"] == "efinance":
            case["tokens"] = ensure_option(case["tokens"], "--market", "A_stock")
        elif case["path"] == "stock price snapshot" and case["backend"] == "efinance":
            case["tokens"] = ensure_option(case["tokens"], "--market", "A_stock")
        elif case["path"] == "stock profile" and case["backend"] == "efinance":
            case["tokens"] = ensure_option(case["tokens"], "--market", "A_stock")
    return cases


def build_case_index(results: list[dict[str, Any]]) -> str:
    """构建结果索引，便于在超长报告中快速定位单条命令。"""

    if not results:
        return '<p class="muted">暂无已完成用例，报告会在第一条命令结束后自动刷新。</p>'
    links = []
    for index, item in enumerate(results, start=1):
        status_class = {
            "PASS": "ok",
            "FAIL": "danger",
            "TIMEOUT": "warn",
        }.get(item["status"], "warn")
        links.append(
            f'<a class="case-chip {status_class}" href="#case-{index}">'
            f'#{index} {escape(item["path"])} [{escape(item["status"])}]'
            '</a>'
        )
    return ''.join(links)


def render_counter_rows(items: dict[str, dict[str, Any]]) -> str:
    """渲染统计表行。"""

    if not items:
        return '<tr><td colspan="6">暂无数据</td></tr>'
    return ''.join(
        '<tr>'
        f'<td>{escape(name)}</td>'
        f'<td>{item["total"]}</td>'
        f'<td>{item["pass"]}</td>'
        f'<td>{item["fail"]}</td>'
        f'<td>{item["timeout"]}</td>'
        f'<td>{item["pass_rate"]}%</td>'
        '</tr>'
        for name, item in items.items()
    )


def render_failure_class_rows(items: dict[str, int]) -> str:
    """渲染失败分类统计表。"""

    if not items:
        return '<tr><td colspan="2">暂无失败分类</td></tr>'
    return ''.join(
        f'<tr><td>{escape(name)}</td><td>{count}</td></tr>'
        for name, count in sorted(items.items())
    )


def render_auto_rows(items: dict[str, int]) -> str:
    """渲染 auto 最终 backend 分布表。"""

    if not items:
        return '<tr><td colspan="2">暂无记录</td></tr>'
    return ''.join(
        f'<tr><td>{escape(name)}</td><td>{count}</td></tr>'
        for name, count in sorted(items.items())
    )


def render_case_blocks(results: list[dict[str, Any]]) -> str:
    """渲染逐条真实执行结果。"""

    blocks: list[str] = []
    for index, item in enumerate(results, start=1):
        style = {
            "PASS": "ok",
            "FAIL": "danger",
            "TIMEOUT": "warn",
        }.get(item["status"], "warn")
        stdout_open = " open" if item["status"] != "PASS" else ""
        stderr_open = " open" if item["stderr"] else ""
        blocks.append(
            f"""
<section class="case" id="case-{index}">
  <div class="case-head {style}">
    <span class="case-id">#{index}</span>
    <span class="case-path">{escape(item['path'])}</span>
    <span class="case-status">{escape(item['status'])}</span>
    <span class="case-time">{item['duration_seconds']}s</span>
    <span class="case-backend">requested={escape(str(item['requested_backend']))}</span>
  </div>
  <div class="case-body">
    <p><strong>命令行:</strong> <code>{escape(item['command_text'])}</code></p>
    <p><strong>说明:</strong> {escape(item['note'])}</p>
    <p><strong>模式标签:</strong> {escape(', '.join(item['mode_tags']) or '<none>')}</p>
    <p><strong>退出码:</strong> {escape(str(item['returncode']))} | <strong>失败分类:</strong> {escape(str(item['failure_class']))} | <strong>失败摘要:</strong> {escape(str(item['failure_reason']))}</p>
    <p><strong>真实 auto 兜底:</strong> {item['auto_fallback_used']} | <strong>开始:</strong> {escape(item['started_at'])} | <strong>结束:</strong> {escape(item['finished_at'])}</p>
    <details>
      <summary>backend 元数据</summary>
      <pre>{escape(json.dumps(item['backend_meta'], ensure_ascii=False, indent=2))}</pre>
    </details>
    <details{stdout_open}>
      <summary>stdout</summary>
      <pre>{escape(item['stdout'] or '<empty>')}</pre>
    </details>
    <details{stderr_open}>
      <summary>stderr</summary>
      <pre>{escape(item['stderr'] or '<empty>')}</pre>
    </details>
    <details>
      <summary>产物落盘</summary>
      <pre>{escape(json.dumps(item['artifact_reports'], ensure_ascii=False, indent=2))}</pre>
    </details>
  </div>
</section>
"""
        )
    return ''.join(blocks)


def render_html(payload: dict[str, Any]) -> str:
    """按照本次测试要求渲染阶段性 HTML 报告。

    Args:
        payload: 已汇总的报告数据。

    Returns:
        可直接落盘的完整 HTML 文本。
    """

    summary = payload["summary"]
    results = payload["results"]
    case_total = payload["case_total"]
    current_case = escape(payload.get("current_case") or "暂无，等待调度或已经完成。")
    mode_text = escape(', '.join(summary["matrix"]["mode_tags"]))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(REPORT_STEM)}</title>
<style>
:root {{
  --essay-text:#171d24;
  --essay-text-strong:#0f141a;
  --essay-text-muted:#42505c;
  --essay-kicker:#5b6976;
  --essay-border:#d5dde5;
  --essay-border-soft:#e2e8ef;
  --essay-panel-bg:#f8fbfd;
  --essay-panel-strong-bg:#eef4f8;
  --essay-hero-bg-start:#f3f8fb;
  --essay-hero-bg-end:#edf4f8;
  --essay-hero-grid:rgba(61,93,119,.05);
  --essay-summary-bg:rgba(255,255,255,.84);
  --essay-button-bg:#f3f7fa;
  --essay-button-text:#16202a;
  --essay-button-active-bg:#182531;
  --essay-button-active-text:#f6fbff;
  --essay-code-bg:#eef4f8;
  --essay-code-inline-bg:#e7eff4;
  --essay-code-text:#12202d;
  --essay-output-bg:#182531;
  --essay-output-text:#edf7ff;
  --essay-link:#205f86;
  --essay-link-border:rgba(32,95,134,.34);
  --essay-accent:#3f7aa2;
  --ok:#1f6f54;
  --ok-bg:#e6f4ec;
  --warn:#8f5a16;
  --warn-bg:#fef3e2;
  --danger:#8a2f33;
  --danger-bg:#fce8e8;
  --shadow:0 22px 70px rgba(27,48,66,.10);
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  color:var(--essay-text);
  background:radial-gradient(circle at top right, rgba(46,111,151,.16), transparent 24%), linear-gradient(180deg, #edf4f8 0%, #f3f7fa 100%);
  font-family:"Georgia","Times New Roman","Noto Serif SC",serif;
  line-height:1.88;
}}
code, pre {{ font-family:"Cascadia Code","Consolas",monospace; }}
pre {{
  margin:0;
  padding:1rem;
  overflow-x:auto;
  white-space:pre-wrap;
  word-break:break-word;
  background:var(--essay-output-bg);
  color:var(--essay-output-text);
  border:1px solid var(--essay-border);
  line-height:1.6;
  font-size:.84rem;
}}
:where(p,li,td,th) > code {{
  padding:.08rem .32rem;
  background:var(--essay-code-inline-bg);
  color:var(--essay-code-text);
}}
.nav {{
  position:sticky;
  top:0;
  z-index:10;
  backdrop-filter:blur(10px);
  background:rgba(255,255,255,.82);
  border-bottom:1px solid var(--essay-border);
}}
.nav-inner {{
  max-width:1280px;
  margin:0 auto;
  padding:.75rem 1rem;
  display:flex;
  gap:.8rem;
  flex-wrap:wrap;
  font-size:.9rem;
}}
.nav-inner a {{ color:var(--essay-link); text-decoration:none; }}
.nav-inner a:hover {{ text-decoration:underline; }}
.page {{ max-width:1280px; margin:0 auto; padding:28px 18px 72px; }}
.hero {{
  position:relative;
  overflow:hidden;
  padding:2.35rem 2rem 1.9rem;
  border:1px solid var(--essay-border);
  background:linear-gradient(180deg, var(--essay-hero-bg-start) 0%, var(--essay-hero-bg-end) 100%);
  box-shadow:var(--shadow);
}}
.hero::before {{
  content:"";
  position:absolute;
  inset:0;
  background-image:linear-gradient(var(--essay-hero-grid) 1px, transparent 1px), linear-gradient(90deg, var(--essay-hero-grid) 1px, transparent 1px);
  background-size:100% 1.7rem, 1.7rem 100%;
  pointer-events:none;
}}
.hero > * {{ position:relative; z-index:1; }}
.kicker {{ margin:0 0 .9rem; font-size:.82rem; letter-spacing:.18em; text-transform:uppercase; color:var(--essay-kicker); }}
.hero h1 {{ margin:0; font-size:clamp(2rem,4vw,3rem); line-height:1.14; color:var(--essay-text-strong); }}
.hero p {{ margin:.75rem 0 0; color:var(--essay-text-muted); }}
.summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.9rem; margin-top:1.5rem; }}
.summary-card {{ padding:.95rem 1rem; border:1px solid var(--essay-border); background:var(--essay-summary-bg); }}
.summary-card strong {{ display:block; margin-bottom:.35rem; font-size:.94rem; color:var(--essay-text-strong); }}
.summary-card .num {{ font-size:2rem; font-weight:700; }}
.section {{ margin-top:2rem; }}
.section h2 {{ margin:0 0 1rem; font-size:1.6rem; color:var(--essay-text-strong); }}
.panel {{ padding:1rem 1.1rem; border:1px solid var(--essay-border); background:var(--essay-panel-bg); box-shadow:var(--shadow); }}
.panel p {{ margin:.55rem 0; }}
.muted {{ color:var(--essay-text-muted); }}
.case-index {{ display:flex; flex-wrap:wrap; gap:.55rem; }}
.case-chip {{ padding:.38rem .62rem; border:1px solid var(--essay-border); background:var(--essay-button-bg); color:var(--essay-button-text); text-decoration:none; font-size:.82rem; }}
.case-chip.ok {{ border-color:rgba(31,111,84,.35); }}
.case-chip.warn {{ border-color:rgba(143,90,22,.35); }}
.case-chip.danger {{ border-color:rgba(138,47,51,.35); }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:.74rem .8rem; text-align:left; border-bottom:1px solid var(--essay-border); vertical-align:top; }}
th {{ background:var(--essay-panel-strong-bg); }}
.case {{ margin-top:1rem; border:1px solid var(--essay-border); background:#fff; box-shadow:var(--shadow); }}
.case-head {{ display:flex; gap:.85rem; flex-wrap:wrap; align-items:center; padding:.78rem .95rem; }}
.case-head.ok {{ background:var(--ok-bg); border-left:4px solid var(--ok); }}
.case-head.warn {{ background:var(--warn-bg); border-left:4px solid var(--warn); }}
.case-head.danger {{ background:var(--danger-bg); border-left:4px solid var(--danger); }}
.case-id {{ min-width:3rem; color:var(--essay-text-muted); font-weight:700; }}
.case-path {{ flex:1; font-weight:700; font-family:"Cascadia Code","Consolas",monospace; }}
.case-status {{ font-weight:700; }}
.case-time, .case-backend {{ color:var(--essay-text-muted); font-size:.86rem; }}
.case-body {{ padding:1rem 1.05rem 1.2rem; }}
.case-body p {{ margin:.45rem 0; }}
details {{ margin-top:.72rem; }}
details summary {{ cursor:pointer; color:var(--essay-link); }}
</style>
</head>
<body>
<div class="nav">
  <div class="nav-inner">
    <a href="#summary">概览</a>
    <a href="#coverage">覆盖协议</a>
    <a href="#status">阶段统计</a>
    <a href="#details">逐条输出</a>
  </div>
</div>
<div class="page">
  <section class="hero" id="summary">
    <p class="kicker">Real API Regression</p>
    <h1>{escape(REPORT_STEM)}</h1>
    <p>本报告强制使用 <code>{escape(str(base.VENV_PYTHON))}</code> 调用真实 CLI 与真实第三方 API，不使用系统 Python，不做 mock。报告从测试开始即持续落盘到目标 HTML。</p>
    <p>开始时间: {escape(payload['started_at'])} | 结束时间: {escape(str(payload.get('finished_at') or '进行中'))} | 进度: {len(results)} / {case_total}</p>
    <p><strong>当前执行:</strong> {current_case}</p>
    <div class="summary-grid">
      <div class="summary-card"><strong>计划用例</strong><span class="num">{case_total}</span></div>
      <div class="summary-card"><strong>已完成</strong><span class="num">{len(results)}</span></div>
      <div class="summary-card"><strong>通过</strong><span class="num">{summary['pass']}</span></div>
      <div class="summary-card"><strong>失败</strong><span class="num">{summary['fail']}</span></div>
      <div class="summary-card"><strong>超时</strong><span class="num">{summary['timeout']}</span></div>
      <div class="summary-card"><strong>平均耗时</strong><span class="num">{summary['avg_duration_seconds']}s</span></div>
    </div>
  </section>

  <section class="section" id="coverage">
    <h2>任务定约与覆盖协议</h2>
    <div class="panel">
      <p><strong>Objective:</strong> 基于当前源码对 52 个叶子命令做真实 CLI / 真实第三方 API 回归，覆盖 shared 多后端、provider 扩展命令、关键模式和业务参数。</p>
      <p><strong>Constraints:</strong> 使用项目 <code>.venv</code> 解释器；记录真实 stdout / stderr；报告持续落盘到 <code>{escape(str(REPORT_HTML))}</code>；不改业务实现。</p>
      <p><strong>Verification:</strong> 先做源码级覆盖矩阵校验，再逐条执行真实命令，写入 JSON / RAW JSON / HTML 三份产物。</p>
      <p><strong>命令覆盖:</strong> {summary['matrix']['expected_command_count']} 条</p>
      <p><strong>shared auto 覆盖:</strong> {summary['matrix']['shared_auto_covered']} / {summary['matrix']['shared_auto_target']}</p>
      <p><strong>显式 backend 覆盖:</strong> {summary['matrix']['explicit_backend_covered']} / {summary['matrix']['explicit_backend_target']}</p>
      <p><strong>业务参数覆盖:</strong> {summary['matrix']['business_option_covered']} / {summary['matrix']['business_option_target']}</p>
      <p><strong>关键模式标签:</strong> {mode_text}</p>
      <p><strong>默认路由样本:</strong> {summary['matrix']['default_route_samples']}</p>
    </div>
  </section>

  <section class="section" id="status">
    <h2>阶段统计</h2>
    <div class="panel">
      <p><strong>当前累计通过率:</strong> {summary['pass_rate']}%</p>
      <p><strong>累计中位耗时:</strong> {summary['median_duration_seconds']}s</p>
      <p><strong>报告 JSON:</strong> <code>{escape(str(RESULT_JSON))}</code></p>
      <p><strong>原始 JSON:</strong> <code>{escape(str(RAW_JSON))}</code></p>
      <p><strong>产物目录:</strong> <code>{escape(str(ARTIFACT_DIR))}</code></p>
    </div>
  </section>

  <section class="section">
    <h2>按分类统计</h2>
    <div class="panel table-wrap">
      <table>
        <thead><tr><th>分类</th><th>总数</th><th>通过</th><th>失败</th><th>超时</th><th>通过率</th></tr></thead>
        <tbody>{render_counter_rows(summary['category_stats'])}</tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <h2>按 backend 统计</h2>
    <div class="panel table-wrap">
      <table>
        <thead><tr><th>requested backend</th><th>总数</th><th>通过</th><th>失败</th><th>超时</th><th>通过率</th></tr></thead>
        <tbody>{render_counter_rows(summary['backend_stats'])}</tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <h2>失败分类与 auto 兜底</h2>
    <div class="panel table-wrap">
      <p><strong>auto 用例总数:</strong> {summary['auto_stats']['total']}</p>
      <p><strong>真实发生 fallback:</strong> {summary['auto_stats']['fallback_used']}</p>
      <p><strong>无最终 backend 且失败:</strong> {summary['auto_stats']['all_failed_without_final_backend']}</p>
      <table>
        <thead><tr><th>失败分类</th><th>次数</th></tr></thead>
        <tbody>{render_failure_class_rows(summary['failure_class_counter'])}</tbody>
      </table>
      <br>
      <table>
        <thead><tr><th>auto 最终 backend</th><th>次数</th></tr></thead>
        <tbody>{render_auto_rows(summary['auto_stats']['final_backend_counts'])}</tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <h2>结果索引</h2>
    <div class="panel case-index">
      {build_case_index(results)}
    </div>
  </section>

  <section class="section" id="details">
    <h2>逐条真实执行输出</h2>
    <div class="panel">
      <p class="muted">以下记录保留每条命令的真实执行命令、耗时、退出码、backend 元数据、stdout、stderr 和副作用产物。报告会在执行过程中持续更新。</p>
    </div>
    {render_case_blocks(results)}
  </section>
</div>
</body>
</html>"""


def write_text(path: Path, content: str) -> None:
    """以 UTF-8 无 BOM 写入文本。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_payload(
    cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
    matrix: dict[str, Any],
    started_at: str,
    finished_at: str | None,
    current_case: str | None,
) -> None:
    """同步刷新 JSON / RAW JSON / HTML 三份产物。

    Args:
        cases: 计划执行的全部用例。
        results: 当前已完成的执行结果。
        matrix: 覆盖矩阵校验结果。
        started_at: 本轮回归开始时间。
        finished_at: 本轮回归完成时间；未完成时传 None。
        current_case: 当前正在执行或当前阶段说明。
    """

    payload = {
        "started_at": started_at,
        "finished_at": finished_at,
        "generated_at": base.now_iso(),
        "python": str(base.VENV_PYTHON),
        "cwd": str(PROJECT_ROOT),
        "case_total": len(cases),
        "current_case": current_case,
        "cases": cases,
        "results": results,
        "summary": base.summarize(results, matrix),
    }
    write_text(RESULT_JSON, json.dumps(payload, ensure_ascii=False, indent=2))
    write_text(
        RAW_JSON,
        json.dumps(
            {
                "started_at": started_at,
                "finished_at": finished_at,
                "current_case": current_case,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    write_text(REPORT_HTML, render_html(payload))


def main() -> None:
    """执行 2026-06-04 专用全量真实回归。"""

    if not base.VENV_PYTHON.exists():
        raise FileNotFoundError(f"未找到项目解释器: {base.VENV_PYTHON}")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = base.now_iso()
    cases = build_cases()
    matrix = base.validate_cases(cases)
    results: list[dict[str, Any]] = []
    save_payload(
        cases,
        results,
        matrix,
        started_at,
        None,
        current_case="回归准备中，正在生成初始报告与覆盖矩阵。",
    )
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        current_case = f"[{index:03d}/{total:03d}] {case['path']} requested={case['backend']}"
        save_payload(cases, results, matrix, started_at, None, current_case=current_case)
        print(f"[{index:03d}/{total:03d}] START {case['path']} requested={case['backend']}", flush=True)
        result = base.run_case(case)
        results.append(result)
        print(
            f"[{index:03d}/{total:03d}] {result['status']:<7} {result['duration_seconds']:>8.3f}s {case['path']} requested={case['backend']}",
            flush=True,
        )
        if result["failure_class"]:
            print(f"           failure={result['failure_class']}", flush=True)
        save_payload(cases, results, matrix, started_at, None, current_case=current_case)
    finished_at = base.now_iso()
    save_payload(
        cases,
        results,
        matrix,
        started_at,
        finished_at,
        current_case="全部用例执行完成，正在汇总最终结论。",
    )
    summary = base.summarize(results, matrix)
    print(
        f"完成: total={len(cases)} pass={summary['pass']} fail={summary['fail']} timeout={summary['timeout']} pass_rate={summary['pass_rate']}% html={REPORT_HTML}",
        flush=True,
    )


if __name__ == "__main__":
    main()
