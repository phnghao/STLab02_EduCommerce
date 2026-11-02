"""Data-driven test runner for STLab02 Requirement Execution."""
from pathlib import Path
import csv, datetime, html, json, time
from collections import Counter
import pandas as pd
from ecommerce_app import fixture

ROOT = Path(__file__).resolve().parent
REQUIRED_COLUMNS = [
    'test_case_id', 'requirement_id', 'condition_id', 'scenario_id', 'title',
    'priority', 'precondition', 'fixture_key', 'input_json', 'expected_type',
    'expected_json', 'execution_status', 'actual_result', 'error_message', 'evidence_reference'
]

def execute_case(row):
    start_time = time.perf_counter()
    tc_id = row.get('test_case_id', 'UNKNOWN')
    try:
        app, user, cart = fixture(row['fixture_key'])
        inp = json.loads(row['input_json'])
        exp = json.loads(row['expected_json'])
    except Exception as setup_err:
        elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            **row,
            'execution_status': 'BLOCKED',
            'actual_result': json.dumps({'setup_error': str(setup_err)}),
            'error_message': f'SETUP/PARSE ERROR: {setup_err}',
            'execution_time_ms': elapsed,
            'executed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    action = inp.get('action')
    actual_data = {}
    error_msg = ''
    passed = False

    try:
        if action == 'catalog_get':
            prod = app.catalog.get(inp['sku'])
            actual_data = {'sku': prod.sku, 'price': str(prod.price), 'active': prod.active}

        elif action == 'cart_add_seq':
            for sku, qty in inp['items']:
                cart.add(sku, qty)
            total_qty = sum(x.quantity for x in cart.lines)
            actual_data = {
                'lines_count': len(cart.lines),
                'total_qty': total_qty,
                'subtotal': str(cart.subtotal())
            }

        elif action == 'shipping_calc':
            fee = app.shipping.calculate(cart.subtotal(), inp['area'])
            actual_data = {'shipping_fee': str(fee)}

        elif action == 'checkout':
            order = app.place(
                user, cart,
                area=inp.get('area', 'inner'),
                voucher=inp.get('voucher'),
                method=inp.get('method', 'COD'),
                approved=inp.get('approved', True),
                key=tc_id
            )
            actual_data = {
                'status': order.status,
                'total': str(order.total),
                'charges_count': len(app.payments.charges),
                'orders_count': len(app.orders),
                'voucher_used': ('SAVE10' in user.used_codes)
            }

        elif action == 'atomicity_check':
            for sku, qty in inp['items']:
                cart.add(sku, qty)
            order = app.place(user, cart, method='COD', key=tc_id)
            actual_data = {
                'status': order.status,
                'stock_A': app.catalog.products['A'].stock,
                'stock_B': app.catalog.products['B'].stock,
                'orders_count': len(app.orders)
            }

        elif action == 'payment_safety':
            order = app.place(user, cart, method=inp['method'], key=tc_id)
            actual_data = {
                'status': order.status,
                'stock_A': app.catalog.products['A'].stock,
                'orders_count': len(app.orders)
            }
        else:
            raise RuntimeError(f'UNKNOWN_ACTION: {action}')

    except ValueError as ve:
        error_msg = str(ve)
        actual_data = {
            'error': error_msg,
            'stock_A': app.catalog.products['A'].stock,
            'stock_B': app.catalog.products['B'].stock,
            'orders_count': len(app.orders),
            'voucher_used': ('SAVE10' in user.used_codes)
        }
    except Exception as unexpected_err:
        elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            **row,
            'execution_status': 'BLOCKED',
            'actual_result': json.dumps({'unexpected_error': str(unexpected_err)}),
            'error_message': str(unexpected_err),
            'execution_time_ms': elapsed,
            'executed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    # Compare only keys specified in expected_json (Oracle verification)
    filtered_actual = {k: actual_data.get(k) for k in exp.keys()}
    if row['expected_type'] == 'EXCEPTION':
        passed = (error_msg != '') and (filtered_actual == exp)
    else:
        passed = (error_msg == '') and (filtered_actual == exp)

    elapsed = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        **row,
        'execution_status': 'PASS' if passed else 'FAIL',
        'actual_result': json.dumps(filtered_actual),
        'error_message': error_msg,
        'execution_time_ms': elapsed,
        'executed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def run_suite(csv_path=None, out_dir=None):
    csv_path = Path(csv_path or ROOT / 'TestCases.csv')
    output = Path(out_dir or ROOT / 'reports')
    output.mkdir(exist_ok=True, parents=True)

    with csv_path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing_cols:
            raise ValueError(f'MISSING_REQUIRED_COLUMNS: {missing_cols}')
        testcases = list(reader)

    ids = [x['test_case_id'] for x in testcases]
    if len(ids) != len(set(ids)):
        raise ValueError('DUPLICATE_TEST_CASE_IDS')

    results = [execute_case(x) for x in testcases]
    df = pd.DataFrame(results)

    summary = df.groupby(['requirement_id', 'execution_status']).size().unstack(fill_value=0).reset_index()
    for col in ['PASS', 'FAIL', 'BLOCKED']:
        if col not in summary.columns:
            summary[col] = 0
    summary['Total'] = summary['PASS'] + summary['FAIL'] + summary['BLOCKED']
    summary['Pass_Rate (%)'] = (summary['PASS'] / summary['Total'] * 100).round(1)

    counts = Counter(df['execution_status'])
    totals = pd.DataFrame([{
        'total_cases': len(df),
        'passed': counts.get('PASS', 0),
        'failed': counts.get('FAIL', 0),
        'blocked': counts.get('BLOCKED', 0),
        'pass_rate_percent': round(100 * counts.get('PASS', 0) / len(df), 1) if len(df) else 0
    }])

    df.to_csv(output / 'test_execution.csv', index=False, encoding='utf-8-sig')
    with pd.ExcelWriter(output / 'test_report.xlsx', engine='openpyxl') as xls:
        df.to_excel(xls, index=False, sheet_name='Execution')
        summary.to_excel(xls, index=False, sheet_name='Traceability')
        totals.to_excel(xls, index=False, sheet_name='Summary')

    rows_html = ''.join(
        '<tr>' + ''.join(
            f'<td>{html.escape(str(r.get(k, "")))}</td>'
            for k in ['test_case_id', 'requirement_id', 'condition_id', 'scenario_id', 'expected_json', 'actual_result', 'execution_status', 'execution_time_ms']
        ) + '</tr>'
        for r in results
    )
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>EduCommerce Test Report</title>
    <style>body{{font:14px Arial;margin:30px;color:#14233c}}h1{{color:#17385f}}table{{border-collapse:collapse;width:100%}}
    td,th{{border:1px solid #cbd5e1;padding:8px;text-align:left}}th{{background:#16385e;color:white}}
    tr:nth-child(even){{background:#f1f5f9}}.metric{{display:inline-block;margin:10px;padding:14px;border-radius:10px;background:#edf3f9;font-size:20px;font-weight:bold}}</style>
    </head><body><h1>EduCommerce Automated Test Execution Report</h1>
    <div class="metric">Total: {len(df)}</div>
    <div class="metric" style="color:#16a34a">PASS: {counts.get("PASS", 0)}</div>
    <div class="metric" style="color:#dc2626">FAIL: {counts.get("FAIL", 0)}</div>
    <div class="metric" style="color:#d97706">BLOCKED: {counts.get("BLOCKED", 0)}</div>
    <div class="metric">Pass Rate: {totals['pass_rate_percent'].iloc[0]}%</div>
    <h2>Traceability & Execution Details</h2>
    <table><tr><th>Case ID</th><th>REQ</th><th>Condition</th><th>Scenario</th><th>Expected</th><th>Actual</th><th>Status</th><th>Time (ms)</th></tr>
    {rows_html}</table></body></html>"""
    (output / 'test_dashboard.html').write_text(page, encoding='utf-8')

    print(f"Executed {len(df)} | PASS {counts.get('PASS',0)} | FAIL {counts.get('FAIL',0)} | BLOCKED {counts.get('BLOCKED',0)}")
    print("\n--- SUMMARY BY REQUIREMENT ---")
    print(summary.to_string(index=False))
    print("\n--- FAILED TEST CASES ---")
    print(df.loc[df['execution_status'] == 'FAIL', ['test_case_id', 'requirement_id', 'expected_json', 'actual_result', 'error_message']].to_string(index=False))
    return df, output

if __name__ == '__main__':
    run_suite()