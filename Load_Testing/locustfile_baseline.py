from locust import HttpUser, task, between

class LandingPageUser(HttpUser):
    # Simulates a user waiting 1 to 3 seconds between clicks
    wait_time = between(1, 3)

    @task
    def load_landing_page(self):
        # Hits the root URL handled by your Nginx container
        self.client.get("/")