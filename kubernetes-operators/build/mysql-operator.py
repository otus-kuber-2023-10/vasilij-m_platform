import kopf
import yaml
import kubernetes
import time
from jinja2 import Environment, FileSystemLoader


def render_template(filename, vars_dict):
    """Returns JSON from rendered YAML manifest"""

    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(filename)
    yaml_manifest = template.render(vars_dict)
    json_manifest = yaml.load(yaml_manifest, Loader=yaml.loader.SafeLoader)
    return json_manifest


def delete_success_jobs(mysql_instance_name):
    """Deletes success ended jobs"""

    print("start deletion")
    api = kubernetes.client.BatchV1Api()
    jobs = api.list_namespaced_job('default')
    for job in jobs.items:
        jobname = job.metadata.name
        if (jobname == f"backup-{mysql_instance_name}-job") or (jobname == f"restore-{mysql_instance_name}-job"):
            if job.status.succeeded == 1:
                api.delete_namespaced_job(jobname, 'default', propagation_policy='Background')
                

def wait_until_job_end(jobname):
    """Waits until the job is completed"""

    api = kubernetes.client.BatchV1Api()
    job_finished = False
    jobs = api.list_namespaced_job('default')
    while (not job_finished) and any(job.metadata.name == jobname for job in jobs.items):
        time.sleep(1)
        jobs = api.list_namespaced_job('default')
        for job in jobs.items:
            if job.metadata.name == jobname:
                print(f"job with { jobname }  found,wait untill end")
                if job.status.succeeded == 1:
                    print(f"job with { jobname }  success")
                    job_finished = True


@kopf.on.create('otus.homework', 'v1', 'mysqls')
def mysql_on_create(body, spec, logger, **kwargs):
    """Runs when MySQL objects are created."""

    # Saving the contents of the MySQL description from CR into variables
    name = body['metadata']['name']
    image = spec['image']
    password = spec['password']
    database = spec['database']
    storage_size = spec['storage_size']

    # Generating JSON manifests for deploy
    persistent_volume = render_template(filename='mysql-pv.yml.j2', 
                                        vars_dict={
                                            'name': name, 
                                            'storage_size': storage_size
                                        })
    persistent_volume_claim = render_template(filename='mysql-pvc.yml.j2', 
                                              vars_dict={
                                                  'name': name, 
                                                  'storage_size': storage_size
                                              })
    service = render_template(filename='mysql-service.yml.j2', 
                              vars_dict={
                                  'name': name
                              })
    deployment = render_template(filename='mysql-deployment.yml.j2', 
                                 vars_dict={
                                     'name': name, 
                                     'image': image, 
                                     'password': password, 
                                     'database': database
                                 })
    restore_job = render_template(filename='restore-job.yml.j2', 
                                  vars_dict={
                                    'name': name,
                                    'image': image,
                                    'password': password,
                                    'database': database
                                  })
    
    # Determining that the created pvc, service and deployment are child resources to mysql custom resource
    # Thus, when deleting a CR, all pvc, service and deployment associated with it will be deleted
    kopf.append_owner_reference(persistent_volume_claim, owner=body)
    kopf.append_owner_reference(service, owner=body)
    kopf.append_owner_reference(deployment, owner=body)
    kopf.append_owner_reference(restore_job, owner=body)
    
    # Creating pv, pvc for mysql data and svc
    logger.info("Creating pv, pvc for mysql data and svc...")
    api = kubernetes.client.CoreV1Api()
    api.create_persistent_volume(persistent_volume)
    api.create_namespaced_persistent_volume_claim('default', persistent_volume_claim)
    api.create_namespaced_service('default', service)

    # Creating backup pv and pvc
    try:
        backup_pv = render_template('backup-pv.yml.j2', {'name': name})
        api = kubernetes.client.CoreV1Api()
        api.create_persistent_volume(backup_pv)
    except kubernetes.client.rest.ApiException:
        pass

    try:
        backup_pvc = render_template('backup-pvc.yml.j2', {'name': name})
        api = kubernetes.client.CoreV1Api()
        api.create_namespaced_persistent_volume_claim('default', backup_pvc)
    except kubernetes.client.rest.ApiException:
        pass
    
    # Creating mysql deployment
    logger.info("Creating mysql deployment...")
    api = kubernetes.client.AppsV1Api()
    api.create_namespaced_deployment('default', deployment)
    try_count = 0

    while True:
        try:
            response = api.read_namespaced_deployment_status(name, 'default')
            if response.status.available_replicas != 1:
                logger.info("Waiting for mysql deployment to become ready...")
            else:
                if try_count > 20:
                    logger.error("mysql deployment is in unavailable state too long...")
                break
        except kubernetes.client.exceptions.ApiException as e:
            raise e
        
        time.sleep(10)
        try_count += 1

    # Trying to restore from backup
    try:
        logger.info("Trying to restore from backup...")
        api = kubernetes.client.BatchV1Api()
        api.create_namespaced_job('default', restore_job)
        response = api.read_namespaced_job_status(f'restore-{name}-job', 'default')
        logger.info(response.status)
    except kubernetes.client.rest.ApiException as e:
        raise e
    
    message = f"MySQL instance {name} and its children resources created!"
    logger.info(message)
    return {'message': message}

@kopf.on.delete('otus.homework', 'v1', 'mysqls')
def delete_object_make_backup(body, spec, logger, **kwargs):
    """Creates backup and delete MySQL object with child resources"""

    name = body['metadata']['name']
    image = spec['image']
    password = spec['password']
    database = spec['database']

    delete_success_jobs(name)

    # Creating backup job
    api = kubernetes.client.BatchV1Api()
    backup_job = render_template(filename='backup-job.yml.j2',
                                 vars_dict={
                                    'name': name,
                                    'image': image,
                                    'password': password,
                                    'database': database
                                 })
    api.create_namespaced_job('default', backup_job)
    wait_until_job_end(f"backup-{name}-job")

    # Deleting pv
    api = kubernetes.client.CoreV1Api()
    api.delete_persistent_volume(f"{name}-pv")
    
    message = f"MySQL instance {name} and its children resources deleted!"
    logger.info(message)
    return {'message': message}
