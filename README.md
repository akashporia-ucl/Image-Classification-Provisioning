# COMP0239 [UCABPOR] Image-Classification-Provisioning

## Overview

This repository contains the infrastructure and configuration for the COMP0239 coursework. It includes Terraform scripts for provisioning resources and Ansible playbooks for configuring and managing the environment.

## Repository Structure

-   **ansible/**: Contains Ansible playbooks and related files for configuring the environment.
    -   **full.yml**: Main playbook that includes all other playbooks.
    -   **inventory.yaml**: Inventory file for Ansible.

-   **terraform/**: Contains Terraform scripts for provisioning infrastructure.
    -   **cloud-init.tmpl.yml**: Cloud-init template for VM initialization.
    -   **generate_inventory.py**: Script to generate Ansible inventory from Terraform outputs.
    -   **lecturer_key.pub**: Public SSH key for the lecturer.
    -   **main.tf**: Main Terraform configuration file.
    -   **outputs.tf**: Terraform outputs configuration.
    -   **providers.tf**: Terraform providers configuration.
    -   **variables.tf**: Terraform variables configuration.
    -   **versions.tf**: Terraform version constraints.

## Prerequisites

Ensure the following software is installed on your system:

1. **Ansible**: For environment configuration and task automation.
2. **Terraform**: For infrastructure provisioning.
3. **Python** (version 3.6 or higher): For running inventory generation scripts.
4. **Screen/Tmux**: (Recommended) For managing long-running processes or sessions.

To install these tools:
- Use your system's package manager (e.g., `apt`, `yum`, or `brew`) or refer to the respective official documentation for installation instructions.


## Ansible

- Ansible playbooks in this repository follow the naming format **p<order of execution>_name**, which helps understand their sequence of execution.

- Ansible install using homebrew:
    ```bash
    brew install ansible
    ```

- Playbooks description: 
    - **p1_configure_basic_tools.yml**
    Installs essential system utilities and development tools required across all nodes, ensuring a consistent baseline environment.

    - **p2_assign_hostnames.yml**
    Assigns meaningful hostnames to each node, facilitating easier identification and management within the cluster.

    - **p3_customise.yml**
    Applies custom configurations and settings tailored to the specific requirements of your deployment environment.

    - **p4_configure_mgmt_nodes.yml**
    Configures management nodes by setting up necessary services and tools to oversee and coordinate cluster operations.

    - **p5_common_keys.yml**
    Generates and distributes common SSH keys to enable secure and password-less authentication between nodes.

    - **p6_share_keys.yml**
    Shares the generated SSH keys among all nodes, establishing trust relationships essential for seamless inter-node communication.

    - **p7_userfile.yml**
    Creates and configures user accounts and associated files, ensuring proper access controls and user environment setups.

    - **p8_hadoop_firewall.yml**
    Configures firewall settings to allow necessary network traffic for Hadoop components, enhancing security while maintaining functionality.

    - **p9_install_hadoop.yml**
    Installs Hadoop across the designated nodes, laying the foundation for distributed data processing capabilities.

    - **p10_config_mgmt.yml**
    Configures Hadoop management nodes, setting up NameNode and ResourceManager services for cluster coordination.

    - **p11_config_worker.yml**
    Configures Hadoop worker nodes, establishing DataNode and NodeManager services to handle data storage and processing tasks.

    - **p12_start_hadoop.yml**
    Initiates Hadoop services across the cluster, bringing the distributed system into an operational state.

    - **p13_install_spark.yml**
    Installs Apache Spark on the cluster, enabling in-memory data processing and analytics capabilities.

    - **p14_spark_path.yml**
    Sets environment variables and system paths for Spark, ensuring that Spark commands are accessible system-wide.

    - **p15_firewall_spark.yml**
    Adjusts firewall settings to permit necessary network traffic for Spark operations, maintaining security protocols.

    - **p16_start_spark_master.yml**
    Starts the Spark master service, which oversees and manages Spark worker nodes within the cluster.

    - **p17_start_spark_worker.yml**
    Initiates Spark worker services, enabling them to register with the master and participate in data processing tasks.

    - **p18_install_dep.yml**
    Installs additional dependencies required for the application and monitoring tools, ensuring all components function correctly.

    - **p19_prometheus.yml**
    Deploys Prometheus for monitoring cluster metrics, providing visibility into system performance and resource utilisation.

    - **p20_node_exporter.yml**
    Installs Node Exporter on each node, allowing Prometheus to collect hardware and OS-level metrics.

    - **p21_config_prometheus.yml**
    Configures Prometheus settings, including scrape intervals and target nodes, to tailor monitoring to your environment.

    - **p22_spark_metrics.yml**
    Integrates Spark metrics with Prometheus, enabling detailed monitoring of Spark application performance.

    - **p23_grafana.yml**
    Installs Grafana, a visualisation tool that works with Prometheus to display metrics on configurable dashboards.

    - **p24_config_ports.yml**
    Configures necessary network ports across services to ensure proper communication and accessibility.

    - **p25_custom_dashboard.yml**
    Sets up custom Grafana dashboards, providing tailored visual insights into system and application metrics.

    - **p26_remove_unwanted.yml**
    Removes unnecessary packages and files from the system, optimising performance and reducing potential security risks.

    - **p27_setup_env.yml**
    Sets up environment variables and configurations required for the application to run correctly within the cluster.

    - **p28_install_rbmq.yml**
    Installs RabbitMQ, a message broker that facilitates communication between different components of the application.

    - **p29_start_app.yml**
    Deploys and starts the main application, ensuring all services are running and properly configured.

    - **p30_dataset.yml**
    Downloads and prepares the dataset required for the image classification tasks, ensuring data is ready for processing.

    - **p31_install_airflow.yml**
    Installs Apache Airflow, a workflow management platform used to author, schedule, and monitor data pipelines.

    - **p32_start_airflow.yml** Starts Airflow services, including the web server and scheduler, enabling the orchestration of complex workflows.


## Terraform

-   **main.tf**: Defines the main infrastructure resources.
-   **outputs.tf**: Specifies the outputs of the Terraform configuration.
-   **providers.tf**: Configures the providers used by Terraform.
-   **variables.tf**: Defines the variables used in the Terraform configuration.
-   **generate_inventory.py**: Generates Ansible inventory from Terraform outputs.

- Terraform install using homebrew:
  ```bash
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
    ```

## Usage

### Setting Up the Environment

1. Clone the repository:
    ```sh
    git clone https://github.com/akashporia-ucl/Image-Classification-Provisioning
    cd Image-Classification-Provisioning
    ```

2. Initialize and apply the Terraform configuration:

    ```sh
    cd terraform
    terraform init
    terraform apply
    ```

    - Update values in `variable.tf` for username, SSH keys, network, etc., before applying.

3. Generate the Ansible inventory:

    ```sh
    python3 generate_inventory.py
    ```

4. Run the Ansible playbooks:

    ```sh
    cd ../ansible
    ansible-playbook -i inventory.yaml full.yml
    ```

5. Results (e.g., CSV files) will be available in the on the web app via GUI.

### Additional Notes

- Use **screen** or **tmux** to run Terraform and Ansible commands in a persistent session, especially for long-running tasks.
- The execution sequence of playbooks can be inferred from their `p<order>_name` naming convention.

## URLs

- **Spark:** https://spark-ucabpor.comp0235.condenser.arc.ucl.ac.uk/
- **Promtheus:** https://prometheus-ucabpor.comp0235.condenser.arc.ucl.ac.uk/targets
- **Grafana:** https://ucabpor-cons.comp0235.condenser.arc.ucl.ac.uk/ [ Username: *admin* | Password: *admin* ]
- **Web App:** https://react-ucabpor.comp0235.condenser.arc.ucl.ac.uk/ [ Username: *admin* | Password: *admin* ]
- **Airflow:** https://airflow-worker-1-ucabpor.comp0235.condenser.arc.ucl.ac.uk/ [ Username: *admin* | Password: *admin* ]


## Sample ETL run via Airflow
