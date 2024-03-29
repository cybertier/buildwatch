import os
import re
import uuid

from flask import jsonify, abort, make_response, send_file
from flask import request
from flask_restful import Resource, reqparse
from werkzeug.utils import secure_filename

from app import app
from buildwatch.starter import start
from db import db
from models.project import Project as ProjectModel
from models.run import Run as RunModel


class Run(Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('project_id',
                             type=str,
                             help='The id of the project',
                             required=True)
    post_parser.add_argument('previous_run_id',
                             type=int,
                             help='The id of the previous run',
                             required=False)
    post_parser.add_argument('user_set_identifier',
                             type=str,
                             help='The identifier like git hash',
                             required=True)
    post_parser.add_argument(
        'zip_filename',
        type=str,
        help=
        'If the repo is not git managed the name of the zip file you uploaded in advance.',
        required=False)
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('id',
                            type=int,
                            help='id of requested project',
                            required=False)

    def get(self):
        args = Run.get_parser.parse_args(strict=True)
        if args['id'] is not None:
            data = RunModel.query.filter(RunModel.id == int(args['id']))
        else:
            data = RunModel.query.all()

        return jsonify([item.json() for item in data])

    def post(self):
        args = Run.post_parser.parse_args(strict=True)
        zip_filename = args['zip_filename']
        args.pop('zip_filename')
        model = RunModel(**args)
        if zip_filename:
            model.user_submitted_artifact_path = os.path.join(
                app.config['PROJECT_STORAGE_DIRECTORY'], 'zips_uploaded',
                secure_filename(zip_filename))
        self._validate_custom_constraints(model)
        db.session.add(model)
        db.session.commit()
        self._run_created(model.id)
        return jsonify(model.json())

    @staticmethod
    def _run_created(run_id):
        start(run_id)

    @staticmethod
    def _validate_custom_constraints(model):
        project = ProjectModel.query.filter(
            ProjectModel.id == model.project_id)[0]
        if project.git_managed:
            if not re.match("[0-9a-f]{5,40}", model.user_set_identifier):
                abort(404, {
                    'message':
                    'No valid commit hash given in user_set_identifier'
                })
        else:
            if not model.user_submitted_artifact_path or not os.path.exists(
                    model.user_submitted_artifact_path):
                abort(
                    404, {
                        'message':
                        'Reference a previously uploaded zip with zip_filename'
                    })

        if model.previous_run_id is not None:
            try:
                previous_run = RunModel.query.filter(
                    RunModel.id == model.previous_run_id)[0]
                project_previous = ProjectModel.query.filter(
                    ProjectModel.id == previous_run.project_id)[0]
                if project_previous.id != project.id:
                    abort(
                        400, {
                            'message':
                            'Previous run does not belong to the same project'
                        })
            except BaseException:
                model.previous_run_id = None
                # abort(400, {'message': 'Previous run not found'})

    @staticmethod
    def upload_zip():
        """
        Upload zip and get the filename returned so you can later reference it when creating a run...
        """
        file = next(iter(request.files.values()))
        zip_file_name = str(uuid.uuid4()) + '.zip'
        target_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                                  'zips_uploaded')
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        target_file = os.path.join(target_dir, zip_file_name)
        file.save(target_file)
        return zip_file_name

    @staticmethod
    def get_report(id, type):
        """
        Get the json report of buildwatch
        """
        type_to_data = {"json": ("final_report.json", "application/json")}
        if type not in type_to_data:
            abort(404, "This type does not exist")
        run: RunModel = RunModel.query.get(id)
        if not run.diff_tool_output_path:
            abort(
                400,
                f"Seems like the diff toll did not finish for that run... Wait or see the error depending on "
                f"the run status. Status is {run.status}")
        file = os.path.join(run.diff_tool_output_path, type_to_data[type][0])
        if not os.path.exists(file):
            abort(404, "Report file is missing")
        response = make_response(send_file(file))
        response.headers['Content-Type'] = type_to_data[type][1]
        return response
