import os

from app import app


def build_html_report(report_object, run):
    output_path = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                               'run', str(run.id), 'diff_tool_out_put', 'report.html')
