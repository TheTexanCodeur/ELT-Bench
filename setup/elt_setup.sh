#Run the conda env commands directly in the terminal and not through the script
#conda create -y -n elt
#conda activate elt
#conda install -y python=3.11
#pip install -r requirements.txt

#Download the data used in the benchmark
gdown 'https://drive.google.com/uc?id=1qVAzU3kgn_G72QQ4b5zt3e1hwkQcSgDq' 
gdown 'https://drive.google.com/uc?id=1-Gv5g_Yg_YrR-NxH4s2tSEK3VhJQc2Q0'
gdown 'https://drive.google.com/uc?id=11vQqNEWXoPG6sjKytAn7TtFLDMiQa17I'

#Unzip the data used in the benchmark
unzip data_api.zip -d ../data/source/api
unzip data_db.zip -d ../data/source/db
unzip gt.zip -d ../data/ground_truth

cd ../elt-docker
docker compose up -d
docker network create -d bridge elt-docker_elt_network

###NOT NECESSARY FOR THE EL STAGE###
#docker network connect elt-docker_elt_network airbyte-abctl-control-plane

cd ../setup

###NOT NECESSARY FOR THE EL STAGE###
#bash data_setup.sh $(pwd)
#python3 mongo.py --path $(pwd)

#Write the snowflake config in the material initialy given to the agent
python3 write_config.py