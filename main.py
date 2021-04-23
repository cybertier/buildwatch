from flask import request, abort, send_from_directory, render_template
from flask_restful import Api

from app import app
from resources.project import Project
from resources.run import Run

api = Api(app)

api.add_resource(Project, "/project")
api.add_resource(Run, "/run")


@app.route("/run/uploadZip", methods=["GET", "POST"])
def upload_zip():
    return Run.upload_zip()


@app.route("/run/<id>/report/<type>", methods=["GET"])
def get_report(id, type):
    return Run.get_report(id, type)


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/docs")
@app.route("/")
def docs():
    return render_template("docs.html")


@app.before_first_request
def create_tables():
    # db.drop_all()
    db.create_all()


@app.before_request
def check_for_token():
    if app.debug or request.path == "/" or request.path == "/docs":
        return
    try:
        if not request.headers["Authorization"] == f"Bearer {app.config['AUTH_TOKEN']}":
            abort(403)
    except Exception as e:
        app.logger.warn("No auth possible", e)
        abort(403)


if __name__ == "__main__":
    from db import db

    db.init_app(app)
    app.run(host='0.0.0.0', port=app.config["PORT"], debug=app.config["DEBUG"])
