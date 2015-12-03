import logging
from celery.task import task

from streamr.conf import settings
from streamr.sandbox import SandBox
from streamr.exc import UnavailableStream
from streamr.remote.models import Status


log = logging.getLogger(__name__)


@task(ignore_results=True)
def terminate_job(job_node_id, node_keys):
    """Proxy task to terminate a job

    Call `RemoteNodeManager.terminate_job` method to a default instance of
    `RemoteNodeManager`.

    """
    from streamr.remote.managers import RemoteNodeManager

    log.info('Terminating job')
    manager = RemoteNodeManager(settings)
    manager.terminate_job(job_node_id, node_keys)


@task(ignore_results=True)
def run_remote_process(processor):
    """Create a sandboxed environment for the processor and run it

    """
    from streamr.remote.managers import RemoteNodeManager

    log.info('Initializing processor environment...')
    manager = RemoteNodeManager(settings)

    with SandBox():
        status = Status.Succeed

        log.info("Loading processor's input...")
        try:
            manager.load_streams(processor.input.values())
        except UnavailableStream:
            status = Status.Cancelled
        else:
            log.info('Running processor...')
            try:
                output = processor.run()
            except:
                log.exception('Error during processor execution')
                status = Status.Failed
                for ostream in output:
                    manager.notify_ready(ostream, status)
            else:
                log.info("Saving processor's output")
                for ostream in output:
                    manager.store_stream(ostream)

        log.info('Update processor status')
        manager.notify_ready(processor, status)

    return True
