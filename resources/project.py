from flask import jsonify
from flask_restful import Resource
from flask_restful import reqparse

from db import db
from models.project import Project as ProjectModel


class Project(Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name', type=str, help='The name of the project', required=True)
    post_parser.add_argument('git_url', type=str, help='The git url of the project', required=False)
    post_parser.add_argument('git_managed', type=bool, help='If project is managed by git', required=True)
    post_parser.add_argument('cuckoo_analysis_per_run', type=int, help='How many times a run is analysed in cuckoo', required=True)
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('id', type=int, help='id of requested project', required=False)

    def post(self):
        args = Project.post_parser.parse_args(strict=True)
        model = ProjectModel(**args)
        db.session.add(model)
        db.session.commit()
        # TODO: hook for project created
        return jsonify(model.json())

    def get(self):
        args = Project.get_parser.parse_args(strict=True)
        if args['id'] is not None:
            data = ProjectModel.query.filter(ProjectModel.id == int(args['id']))
        else:
            data = ProjectModel.query.all()

        return jsonify([item.json() for item in data])
