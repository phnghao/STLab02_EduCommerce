import gradio as gr
import matplotlib.pyplot as plt
import pandas as pd

report_df = pd.read_csv("reports/test_execution.csv").fillna("")

def dashboard_view(req="ALL", status="ALL"):
    df = report_df.copy()
    if req != "ALL": df = df[df["requirement_id"] == req]
    if status != "ALL": df = df[df["execution_status"] == status]
    summary = df["execution_status"].value_counts().reindex(["PASS", "FAIL", "BLOCKED"], fill_value=0)

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(summary.index, summary.values, color=["#16a34a", "#dc2626", "#d97706"])
    ax.bar_label(bars, padding=3)
    ax.set_title("EduCommerce Test Execution Results")
    ax.set_ylabel("Number of Test Cases")
    ax.set_ylim(0, max(2, int(summary.max()) + 3))
    fig.tight_layout()

    cols = ["test_case_id", "requirement_id", "scenario_id", "expected_json", "actual_result", "execution_status", "execution_time_ms"]
    return fig, df[cols], f"**Executed:** {len(df)} | **PASS:** {summary['PASS']} | **FAIL:** {summary['FAIL']} | **BLOCKED:** {summary['BLOCKED']}"

with gr.Blocks(title="EduCommerce Test Dashboard") as demo:
    gr.Markdown("# EduCommerce Requirement Traceability & Test Results Dashboard")
    with gr.Row():
        req_filter = gr.Dropdown(["ALL"] + sorted(report_df.requirement_id.unique().tolist()), value="ALL", label="Requirement ID")
        status_filter = gr.Dropdown(["ALL", "PASS", "FAIL", "BLOCKED"], value="ALL", label="Execution Status")
    status_line = gr.Markdown()
    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=300):
            chart = gr.Plot(label="Status Distribution")
        with gr.Column(scale=2, min_width=450):
            result_table = gr.Dataframe(label="Test Execution Details", interactive=False, wrap=True)
    gr.File(value="reports/test_report.xlsx", label="Download Excel Report")

    req_filter.change(dashboard_view, [req_filter, status_filter], [chart, result_table, status_line])
    status_filter.change(dashboard_view, [req_filter, status_filter], [chart, result_table, status_line])
    demo.load(dashboard_view, [req_filter, status_filter], [chart, result_table, status_line])

if __name__ == "__main__":
    demo.launch(share=False)