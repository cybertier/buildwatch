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

TODO

# Talking to Buildwatch

See the [github pages docs](https://example.com) or `/docs` when you have executed Buildwatch. 