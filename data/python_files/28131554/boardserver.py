import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import uuid

logging.basicConfig(level=logging.DEBUG)

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/draw", DrawSocketHandler),
        ]
        settings = dict(
            cookie_secret="__NOT_TOO_SECRET__",
            xsrf_cookies=True,
            autoescape=None,
        )
        tornado.web.Application.__init__(self, handlers, settings)


class DrawSocketHandler(tornado.websocket.WebSocketHandler):
    players = set()

    def allow_draft76(self):
        # for iOS 5.0 Safari
        return True

    def open(self):
        DrawSocketHandler.players.add(self)

    def on_close(self):
        DrawSocketHandler.players.remove(self)

    @classmethod
    def send_updates(cls, event):
        logging.info("enviando mensaje a %d jugadores", len(cls.players))
        for player in cls.players:
            try:
                player.write_message(event)
            except:
                logging.error("Error al enviar", exc_info=True)

    def on_message(self, message):
        logging.info("mensaje recibido %r", message)
        parsed = tornado.escape.json_decode(message)
        event = {
            "id": str(uuid.uuid4()),
            "session": parsed["session"],
            "command": parsed["command"],
            "params": parsed["params"],
            }

        DrawSocketHandler.send_updates(event)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
