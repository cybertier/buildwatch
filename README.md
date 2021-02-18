# Buildwatch

Watching your build. Buildwatch can make reports on what behaviour your build shows. To be honest you can not only watch
builds. Maybe you would rather watch your unit tests. No problem for buildwatch. The idea is that you host Buildwatch
somewhere on a standalone server and give it its tasks via a CI pipeline.

### Using git

If you are using git you can just create a project pointing to the git repository and then trigger runs using the git
commit hash. Buildwatch will check out the commit and watch for its behaviour. You should use the .buildwatch.sh file in
the root directory of your repo to define the process you want to have watched. Using buildwatches REST API you can
create the run and ask for its result.

### Using zips

If you are using another VCS or don't have a git repo for other reasons you can also provide zips containing a
.buildwatch.sh.

### Installing dependencies

Either do so in your cuckoo setup or in the .prebuild.sh

# Setup

We quickly describe how to set up the project

## Cuckoo

You need a running cuckoo instance and a cuckoo api. You need to have [this fork](https://github.com/axel1200/cuckoo)
for the setup read its readme and the cuckoo docs. You need to run the daemon `cuckoo -d` and the api `cuckoo api`. The
ip and port of the api need to be given to cuckoo via the configuration.

## Installing Buildwatch

Install requirements from requirements.txt and use python 3 to execute the main.py.

## Configuration

The default configuration can be found in the [/config/default_config.py](config/default_config.py). If you
want to supply your own values and overwrite those provide a similar python file. The path to the file should be
supplied via the `BUILDWATCH_SETTINGS_FILE` environment variable. Buildwatch specific config options:

| Option name        | Default           | Description       |
| ------------- |:-------------| -----|
| SQLALCHEMY_DATABASE_URI | 'sqlite:///sql_lite.db'| The url pointing to the Database used. Can also point to other types of databases than sqlite. |
| SQLALCHEMY_TRACK_MODIFICATIONS | False | No need changing this | 
| SECRETE_KEY | 'secret' | Used for cryptography should be changed in production | 
| PROJECT_STORAGE_DIRECTORY | './storage' | Folder where data Buildwatch persistent data is stored |
| DEBUG | True| Should be false in production |
| AUTH_TOKEN | 'filloutinprod'| Token used to authorize to the Buildwatch rest api |
| CUCKOO_API_URL | 'http://localhost:8090'| The url used to communicate with the cuckoo rest api |
| CUCKOO_API_TOKEN | '5Ql0ClpOzM9oot53daAIvA' | The token for the cuckoo api used to authenticate with it. Can be found in the configuration files of cuckoo. (api_token property in cuckoo.conf) |
| TIME_OUT_WAITING_FOR_CUCKOO | 3\*60\*60 | This many seconds we wait for cuckoo builds to finish |
| TIME_OUT_WAITING_FOR_PREVIOUS_COMMIT | 3\*60\*60 | This many seconds we wait for the previous commit to be of status _prepared. |
| DELAY_CHECKING_CUCKOO_TASK_STATUS | 20| Every x seconds check if the cuckoo task finished. |
| DELAY_CHECKING_PREVIOUS_TASK_STATUS | 20| Every x seconds check if the previous task finished. |
| PORT | 8080| Port Buildwatch rest api is started on |

Other flask or sqlachemy specific options can be found in the corresponding documentation and can be set in this file as
well.

# Talking to Buildwatch

See the [github pages docs](https://example.com) or `/docs` when you have executed Buildwatch.

# Architecture

Here are some diagrams showing how Buildwatch is organised:
![Database](static/achitecture/databse.png)
![Architecture](static/achitecture/architecture.png)
![Pipeline](static/achitecture/Pipeline%20Buildwatch.png)
