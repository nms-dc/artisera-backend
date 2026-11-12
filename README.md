# Dev Setup

### Basic dependencies

* Install docker-compose from [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/) and docker-engine from [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)
* Clone the repository: `git clone https://github.com/SIF-AQUACULTURE/aquaculture-backend.git`
* `cd aquaculture-backend`
* Create `.env` file with following content:

  ```text
    ENV=dev
    SECRET_KEY=dev-use
    POSTGRES_DB=aqua
    POSTGRES_HOST=db
    POSTGRES_PASSWORD=dev-use-only
    POSTGRES_USER=aqua
    AWS_ACCESS_KEY_ID=minio
    AWS_SECRET_ACCESS_KEY=minio123
    AWS_STORAGE_BUCKET_NAME=aqua
    AWS_S3_URL=http://minio:9000
    MINIO_ACCESS_URL=localhost:9000/aqua
  ```

  **Running Project**

* Run `docker-compose up --build`

### Usage

* `docker-compose up` to start all the components
* `docker-compose --build up` to start the components and force a rebuild
* `ctrl+c` to kill the docker stack
* The app can be reached via [http://0.0.0.0:8000/](http://0.0.0.0:8000/)

### Creating a app

* `sudo docker-compose run backend django-admin startapp farms ./backend/apps/farms` to create a app called farms
* NOTE please create a folder inside `aquaculture-backend/backend/backend/apps/farms` first before running the command
