import vertexai
from vertexai import agent_engines  # For the prebuilt templates
from typing import Dict

from personal_clone import config, agent
from dotenv import dotenv_values

vertexai.init(
    project=config.GOOGLE_CLOUD_PROJECT,
    location=config.GOOGLE_CLOUD_LOCATION,
    staging_bucket=config.GOOGLE_CLOUD_STORAGE_BUCKET,
    credentials=config.get_identity_token(),
)

resource_name = (
    "projects/131221610297/locations/us-east4/reasoningEngines/3013365547548016640"
)
requirements = "requirements.txt"
display_name = "personal_clone"
gcs_dir_name = "gs://personalclone"
extra_packages = ["personal_clone/", "installation_scripts/install.sh"]
env_vars: Dict = dotenv_values("personal_clone/.env")
env_vars.pop("GOOGLE_CLOUD_PROJECT")
env_vars.pop("GOOGLE_CLOUD_LOCATION")
build_options: Dict = {"installation_scripts": ["installation_scripts/install.sh"]}


# create
remote_agent = agent_engines.create(
    agent_engine=agent.root_agent,
    requirements=requirements,
    display_name=display_name,
    gcs_dir_name=gcs_dir_name,
    extra_packages=extra_packages,
    env_vars=env_vars,
    build_options=build_options,
)


# #update
# remote_agent = agent_engines.update(
#     resource_name=resource_name,
#     agent_engine=agent.root_agent,
#     requirements=requirements,
#     # display_name=display_name,
#     # gcs_dir_name=gcs_dir_name,
#     # extra_packages=extra_packages,
#     # env_vars=env_vars,
#     build_options=build_options,
# )
