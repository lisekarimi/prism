#!/usr/bin/env python

"""Main entry point for PRISM demo application."""

from prism.app import demo
from prism.constants import GRADIO_PORT
from prism.utils import logger

if __name__ == "__main__":
    logger.info(f"🚀 Starting PRISM Gradio app on port {GRADIO_PORT}")
    demo.launch(server_name="0.0.0.0", server_port=GRADIO_PORT)
