import os
import json
import yaml          # PyYAML ≥ 5.1 needed for sort_keys=False
import subprocess

# Path to save the inventory file
ANSIBLE_FOLDER = "../ansible"
INVENTORY_FILE = os.path.join(ANSIBLE_FOLDER, "inventory.yaml")

def get_terraform_outputs():
    """
    Fetch Terraform outputs as JSON using 'terraform output -json'.
    """
    result = subprocess.run(
        ["terraform", "output", "-json"],
        capture_output=True,
        text=True,
        cwd="."
    )
    if result.returncode != 0:
        print("Failed to fetch Terraform outputs.")
        print(result.stderr)
        exit(1)
    return json.loads(result.stdout)

def generate_ansible_inventory(tf_output):
    """
    Generate an Ansible inventory YAML file from Terraform outputs,
    preserving the order of IPs exactly as they appear in Terraform.
    """
    management_ips = tf_output.get("management_vm_ips", {}).get("value", [])
    storage_ip     = tf_output.get("storage_vm_ip",     {}).get("value")
    worker_ips     = tf_output.get("worker_vm_ips",     {}).get("value", [])

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
                    "hosts": {ip: {} for ip in worker_ips}   # order preserved
                }
            }
        }
    }

    os.makedirs(ANSIBLE_FOLDER, exist_ok=True)
    with open(INVENTORY_FILE, "w") as f:
        yaml.safe_dump(
            inventory,
            f,
            default_flow_style=False,
            sort_keys=False    # ← keeps the insertion order
        )

    print(f"Inventory file created at: {INVENTORY_FILE}")

if __name__ == "__main__":
    tf_outputs = get_terraform_outputs()
    generate_ansible_inventory(tf_outputs)
