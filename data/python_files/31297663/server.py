import eventlet
eventlet.monkey_patch()

from nudge.publisher import serve, Endpoint, Args
import nudge.renderer
import nudge.arg

from gvizds.config import Config
from gvizds.datasource import DataSource


def endpoints(datasource):
    return [
        Endpoint(
            name="query",
            method="GET",
            uri="/query/(?P<table>[^/]*)/?$",
            function=datasource.query,
            args=Args(
                nudge.arg.String('table'),
                tq=nudge.arg.String('tq'),
                tqx=nudge.arg.String('tqx', optional=True),
            ),
            renderer=nudge.renderer.Plain(),
        ),
    ]

if __name__ == '__main__':
    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    config = Config(filename)
    ds = DataSource(config)

    serve(endpoints(ds))
