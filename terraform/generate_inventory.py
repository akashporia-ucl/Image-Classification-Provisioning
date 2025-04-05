import os
import json
import yaml  # Install PyYAML with `pip install pyyaml`
import subprocess

# Define the path to save the inventory file
ANSIBLE_FOLDER = "../ansible"  # Relative path to the ansible folder
INVENTORY_FILE = os.path.join(ANSIBLE_FOLDER, "inventory.yaml")

def get_terraform_outputs():
    """
    Fetch Terraform outputs as JSON using 'terraform output -json'.
    """
    result = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True, cwd=".")
    if result.returncode != 0:
        print("Failed to fetch Terraform outputs.")
        print(result.stderr)
        exit(1)
    return json.loads(result.stdout)

def generate_ansible_inventory(terraform_output):
    """
    Generate Ansible inventory YAML file from Terraform outputs.
    """
    # Extract values safely
    management_ips = terraform_output.get("management_vm_ips", {}).get("value", [])
    storage_ip = terraform_output.get("storage_vm_ip", {}).get("value", None)
    worker_ips = terraform_output.get("worker_vm_ips", {}).get("value", [])

    # Prepare inventory structure in the new format
    inventory = {
        "all": {
            "children": {
                "management": {
                    "hosts": {ip: {} for ip in management_ips}
                },
                "storage": {
                    "hosts": {storage_ip: {}} if storage_ip else {}
                },
                "workers": {
                    "hosts": {ip: {} for ip in worker_ips}
                }
            }
        }
    }

    # Ensure the ansible folder exists
    os.makedirs(ANSIBLE_FOLDER, exist_ok=True)

    # Write the inventory file in YAML format
    with open(INVENTORY_FILE, "w") as f:
        yaml.dump(inventory, f, default_flow_style=False)

    print(f"Inventory file created at: {INVENTORY_FILE}")

# Main execution
if __name__ == "__main__":
    terraform_outputs = get_terraform_outputs()
    generate_ansible_inventory(terraform_outputs)
