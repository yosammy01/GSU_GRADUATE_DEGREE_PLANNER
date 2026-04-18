# GSU Graduate Degree Planner

## Overview
This repository contains the source code and deployment configuration for the GSU Graduate Degree Planner. The application is built using a pure Python/Flask backend with standard HTML templating, designed specifically for high availability and concurrent load handling.

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
```

### Step 2: Build and Run the Docker Cluster
The entire infrastructure (Load Balancer, Web Containers, and Database) is defined in the `docker-compose.yml` file. To build the images and start the containers in the background, run:
```bash
docker compose up --build -d
```

### Step 3: Verify the Deployment
Once the containers are spinning up, you can verify their status:
```bash
docker ps
```
You should see the following containers running actively:
* `gsu_graduate_degree_planner-load_balancer-1` (Mapped to Port 80)
* `gsu_graduate_degree_planner-web1-1` (Port 5000)
* `gsu_graduate_degree_planner-web2-1` (Port 5000)
* `gsu_graduate_degree_planner-db-1` (Port 3306)

The application is now accessible locally via your browser at: `http://localhost`

### Step 4: Shutting Down
To stop the application and remove the containers, run:
```bash
docker compose down
```

---

## 2. Cloud Deployment (Azure VM)

To deploy this application to a production environment like an Azure Virtual Machine, follow these steps:

1. **Provision the VM:** Ensure you have an Ubuntu/Linux VM running in Azure with Docker and Docker Compose installed.
2. **Configure Networking:** Navigate to the Azure Portal -> VM Network Settings -> Inbound Port Rules. Ensure that **Port 80 (HTTP)** and **Port 22 (SSH)** are open to the public internet.
3. **Deploy:** Clone the repository onto the VM and execute the same `docker compose up --build -d` command as used in local development.
4. **Access:** The application will be live at `http://<YOUR_AZURE_PUBLIC_IP>`.

---

## 3. Monitoring and Logging

You can monitor the specific traffic and health of the Flask application nodes in real-time by checking the Docker logs. 

To watch the traffic hit the first Flask container, run:
```bash
docker logs -f gsu_graduate_degree_planner-web1-1
```
To watch the Nginx load balancer routing the traffic, run:
```bash
docker logs -f gsu_graduate_degree_planner-load_balancer-1
```

---

## 4. Load Testing with Locust

This project includes a baseline stress test to verify the hardware bottleneck and load balancer efficacy. 

### Step 1: Set up the Python Environment
Do not install testing tools globally. Create and activate a virtual environment in the project directory:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```
**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
With the `(.venv)` active, install Locust:
```bash
pip install locust
```

### Step 3: Run the Attack
Start the Locust test script:
```bash
locust -f locustfile_baseline.py
```

### Step 4: Configure the Swarm
1. Open a web browser and navigate to the Locust dashboard at `http://localhost:8089`.
2. Enter the target number of concurrent users (e.g., `500`).
3. Enter the spawn rate (e.g., `20` users per second).
4. Enter the target Host URL:
   * For local testing: `http://localhost`
   * For production testing: `http://<YOUR_AZURE_PUBLIC_IP>` (Do not include a trailing slash or port number).
5. Click **Start Swarming** to begin the test and monitor the Requests Per Second (RPS) and Latency metrics.
```
