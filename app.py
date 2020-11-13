from flask import Flask
from flask_restful import Api

from resources.project import Project
from resources.report import Report
from resources.run import Run

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sql_lite.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret'
api = Api(app)

api.add_resource(Project, '/project')
api.add_resource(Run, '/run')
api.add_resource(Report, '/report')


@app.before_first_request
def create_tables():
    # db.drop_all()
    db.create_all()


if __name__ == '__main__':
    from db import db

    db.init_app(app)
    app.run(port=8080, debug=True)
