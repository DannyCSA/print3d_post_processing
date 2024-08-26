# ABS Post-Processing System

## Overview

This project is a post-processing system designed for ABS 3D prints, utilizing acetone vapor for surface smoothing. The system includes a web-based interface and an embedded controller using an ESP32 microcontroller running MicroPython. The goal of the post-processing system is to automate and enhance the acetone vapor smoothing process, providing better control over the environment, safety features, and remote monitoring capabilities.

## Features

- **Web Interface**: Control and monitor your ABS post-processing system remotely via a web browser.
  - **HTML, CSS, JavaScript**: A responsive and user-friendly interface to interact with the post-processing system.
  - **Real-time Monitoring**: View real-time data such as temperature, vapor concentration, and system status.
  
- **Embedded Controller**: An ESP32 microcontroller running MicroPython to interface with various sensors and actuators.
  - **Temperature & Vapor Control**: Monitors and controls the internal environment for optimal acetone vapor smoothing.
  - **Safety Mechanisms**: Includes safety features to prevent over-exposure to acetone vapor and overheating.
