import logging


def configurar_logging(nivel: str) -> None:
    logging.basicConfig(
        level=nivel.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s · %(message)s",
    )
