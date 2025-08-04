# Cognitive Load Project Setup Guide

This guide details the necessary steps to set up the complete development environment for the video analysis application using the pre-built database image.

## System Architecture Overview

The application consists of three main parts:
1.  **Java Backend (Spring Boot):** The main web server.
2.  **Python Analysis Service:** A Flask-based microservice for AI/ML tasks.
3.  **Oracle Database (Docker):** A pre-configured database container.

---

## Step 1: Install Prerequisite Software

Before starting, ensure the following software is installed on your system.

1.  **Git:** For cloning the source code. ([git-scm.com](https://git-scm.com/downloads))
2.  **Java Development Kit (JDK) 21:** ([Oracle JDK 21](https://www.oracle.com/java/technologies/downloads/#jdk21-windows) or a similar distribution)
3.  **Miniconda (or Anaconda):** For managing Python environments. ([docs.conda.io/projects/miniconda](https://docs.conda.io/projects/miniconda/en/latest/index.html))
4.  **Docker Desktop:** To run the database container. ([docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop))
5.  **FFmpeg:** For audio extraction. ([ffmpeg.org/download.html](https://ffmpeg.org/download.html))
    *   **IMPORTANT:** After downloading, add the `bin` directory from the FFmpeg folder to your system's **PATH environment variable**.

---

## Step 2: Project and Database Setup

1.  **Clone the Repository:**
    Open a terminal or Git Bash and clone the project.
    ```bash
    git clone <your-repository-url>
    cd CL-Project
    ```

2.  **Run the Pre-Configured Oracle Database:**
    Open a terminal and run the following command. This will download the custom, pre-configured database image from Docker Hub and start it.
    ```bash
    docker run -d --name oracle-db -p 1521:1521 laoi/cl-project-db:v1
    ```
    *Note: All tables, sequences, and the admin user are already included in this image. No SQL scripting is needed.*

3.  **Set Up Python Environments:**
    Open an Anaconda Prompt or your terminal and navigate to the `python-microservice` directory.
    ```bash
    cd python-microservice
    ```
    Create the two required Conda environments:

    *   **Main Environment (`cl_env`):**
        ```bash
        conda create -n cl_env python=3.10 -y
        conda activate cl_env
        pip install -r requirements.txt
        ```

    *   **OCR Environment (`ocr_env`):**
        ```bash
        conda create -n ocr_env python=3.10 -y
        conda activate ocr_env
        pip install -r core/craft/requirements.txt
        ```

---

## Step 3: Running the Application

To run the application, you must start the services in the correct order. Use **two separate terminals**.

1.  **Terminal 1: Start the Python Analysis Service**
    *   Navigate to the `python-microservice` directory.
    *   Activate the main conda environment.
    *   Run the Flask app.
    ```bash
    cd python-microservice
    conda activate cl_env
    python app.py
    ```
    *This service will run on `http://localhost:5000`.*

2.  **Terminal 2: Start the Java Backend**
    *   Navigate to the root directory of the project (`CL-Project`).
    *   Use the Maven wrapper to run the Spring Boot application.
    ```bash
    # For macOS/Linux:
    ./mvnw spring-boot:run

    # For Windows Command Prompt:
    mvnw.cmd spring-boot:run
    ```
    *This service will run on `http://localhost:8181`.*

---

## Step 4: Verification

1.  Open your web browser and navigate to **`http://localhost:8181`**.
2.  Log in using the pre-configured admin account:
    *   **Username:** `admin`
    *   **Password:** `admin123`
3.  You should have immediate access to all pages, including **User Control** and **Announcements**.
4.  Navigate to the **Analyze** page and upload a video to confirm the entire analysis pipeline is working.
