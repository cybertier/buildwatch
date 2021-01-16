from flask import request, abort
from flask_restful import Api

from app import app
from resources.project import Project
from resources.run import Run

api = Api(app)

api.add_resource(Project, '/project')
api.add_resource(Run, '/run')


@app.route('/run/uploadZip', methods=['GET', 'POST'])
def upload_zip():
    return Run.upload_zip()


@app.route('/run/<id>/report/<type>', methods=['GET'])
def get_report(id, type):
    return Run.get_report(id, type)


@app.before_first_request
def create_tables():
    # db.drop_all()
    db.create_all()


@app.before_request
def check_for_token():
    if not app.debug:
        try:
            if not request.headers['Authorization'] == f"Bearer {app.config['AUTH_TOKEN']}":
                abort(403)
        except Exception as e:
            app.logger.warn("No auth possible", e)
            abort(403)


if __name__ == '__main__':
    from db import db

    db.init_app(app)
    app.run(port=8080, debug=app.config["DEBUG"])
