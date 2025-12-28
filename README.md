# NOC Second Pass tool: Infrastructure & Deployment

## Connectivity & Routing
The application is hosted in an isolated **Docker Swarm** environment but remains accessible via the host's native **Apache** server.

1.  **Public Entry:** The host server (Apache) receives requests at the configured internal URI.
2.  **Reverse Proxy:** Apache forwards traffic to the Docker Nginx container.
3.  **Internal Routing:** * Access the tool via: `http://<PRODUCTION_SERVER_IP>/secpass`
    * A custom `PrefixMiddleware` handles internal routing to ensure link integrity behind the sub-path.


---

## Credentials & Secrets
Credentials are never stored in the code or container image. They are injected at runtime via **Docker Secrets** (found in `/run/secrets/`).

### Updating Credentials
If an API key or password changes, follow these steps to securely update the environment:

1.  **List Existing Secrets**
    ```bash
    docker secret ls
    ```
3.  **Remove the old secret:**
    ```bash
    docker secret rm <SECRET_NAME>
    ```
4.  **Create the updated secret:**
    ```bash
    echo "new_secret_value" | docker secret create <SECRET_NAME> -
    ```
5.  **Apply changes to the Stack:**
    ```bash
    docker stack deploy -c stack.yml audit_tool
    ```
    *Note: Swarm will automatically perform a rolling restart of the container to pick up the new secret.*

---

## Maintenance Commands

| Action | Command | When to run |
| :--- | :--- | :--- |
| **Deploy/Update Stack** | `docker stack deploy -c stack.yml audit_tool` | After changing code, the `stack.yml`, or any secrets. |
| **Check Health** | `docker stack services audit_tool` | To verify if the container is running (1/1) or has crashed (0/1). |
| **View Live Logs** | `docker service logs -f audit_tool_app` | To debug errors or watch the audit output in real-time. |
| **Force Reload** | `docker service update --force audit_tool_app` | To restart the application without changing any configuration files. |

---

## File Structure
For the application to function and deploy correctly, the following structure must be maintained in the root directory:

* **Application Core**
    * `app.py` — Flask entry point with `PrefixMiddleware`.
    * `sec_pass/` — Logic package (API requests, scraping, and data processing).
    * `templates/` — HTML templates for the web interface.
* **Docker & Orchestration**
    * `Dockerfile` — Instructions for the Python/Gunicorn image build.
    * `stack.yml` — Docker Swarm service definitions and secret mapping.
    * `nginx.conf` — Configuration for the internal reverse proxy.
    * `requirements.txt` — List of required Python dependencies.
* **Configuration & Git**
    * `.dockerignore` — Ensures host files (like `venv`) stay out of the image.
    * `.gitignore` — Prevents local junk and secrets from being committed.
