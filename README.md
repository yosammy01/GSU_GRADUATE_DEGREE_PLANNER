# GSU Graduate Degree Planner

## Overview
This repository contains the source code and deployment configuration for the GSU Graduate Degree Planner. The application is built using a Python/Flask backend and is designed for high availability and concurrent load handling. 

The production architecture utilizes Docker Compose to orchestrate an Nginx load balancer distributing traffic across multiple Gunicorn WSGI synchronous worker containers (`web1` and `web2`), alongside a dedicated database container.

## Prerequisites
To build, run, and test this application, ensure the following are installed on your system:
* **Docker & Docker Compose:** For running the application cluster.
* **Python 3.12+:** For running the local load-testing client.
* **Git:** For version control and cloning the repository.

---

## 1. Local Build and Execution

### Step 1: Clone the Repository
Open your terminal and clone the project to your local machine:
```bash
git clone <your-repository-url>
cd gsu_graduate_degree_planner