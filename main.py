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

@app.before_first_request
def create_tables():
    db.drop_all()
    db.create_all()


if __name__ == '__main__':

    from db import db

    db.init_app(app)
    app.run(port=8080, debug=True)
