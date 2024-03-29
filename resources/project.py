from flask import jsonify, abort
from flask_restful import Resource
from flask_restful import reqparse

from db import db
from models.project import Project as ProjectModel


def check_constraints(model: ProjectModel):
    if model.cuckoo_analysis_per_run < 3:
        abort(400, {'message': 'cuckoo_analysis_per_run can not be smaller than 3'})


class Project(Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name', type=str, help='The name of the project', required=True)
    post_parser.add_argument('old_runs_considered', type=int,
                             help='The patterns and '
                                  'reports of such many old runs are used '
                                  'to subtract observables from the current run',
                             required=True)
    post_parser.add_argument('git_url', type=str, help='The git url of the project', required=False)
    post_parser.add_argument('patternson_off', type=bool, help='If patterns should be learned', required=False)
    post_parser.add_argument('git_managed', type=bool, help='If project is managed by git', required=True)
    post_parser.add_argument('cuckoo_analysis_per_run', type=int, help='How many times a run is analysed in cuckoo',
                             required=True)
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('id', type=int, help='id of requested project', required=False)

    def post(self):
        args = Project.post_parser.parse_args(strict=True)
        model = ProjectModel(**args)
        check_constraints(model)
        db.session.add(model)
        db.session.commit()
        return jsonify(model.json())

    def get(self):
        args = Project.get_parser.parse_args(strict=True)
        if args['id'] is not None:
            data = ProjectModel.query.filter(ProjectModel.id == int(args['id']))
        else:
            data = ProjectModel.query.all()

        return jsonify([item.json() for item in data])
