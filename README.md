# Pathfinder: Space Agriculture Technology Demonstrator
### Florida Atlantic University - Senior Design 2026

![Project Status](https://img.shields.io/badge/Status-Prototyping-yellow)
![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi-green)
![Mission](https://img.shields.io/badge/Mission-3U_CubeSat-blue)

## 🛰️ Mission Overview
**Pathfinder** is a 3U CubeSat technology demonstrator designed to validate the mechanical and software infrastructure required for space agriculture. Unlike biological experiments that focus on the plants, Pathfinder focuses on the *systems* that keep them alive:
* Autonomous Environmental Control (Temp, Humidity, CO2).
* Liquid Delivery in Microgravity.
* Data Handling and Telemetry.

## 📂 Repository Structure
* **01_Management:** CDR/PDR Reports, Budgets, and Timelines.
* **02_Systems:** Requirements, CONOPS, and Interface Control Documents.
* **03_Mechanical:** CAD Models (SolidWorks), FEA Analysis, and Drawings.
* **04_Electrical:** Schematics, PCB Layouts, and Wiring Diagrams.
* **05_Software:** On-Board Computer (OBC) Flight Code and Ground Station tools.

## 💻 Flight Software Architecture
The OBC is powered by a **Raspberry Pi 3B+** running Python 3.9+.
* **Architecture:** Finite State Machine (FSM) with Threaded GUI.
* **Sensors:** BME280 (Env), SCD-40 (CO2), Capacitive Soil Moisture.
* **Actuators:** 12V Peristaltic Pump, Grow Lights, Polyimide Heaters.

## 👥 The Team
* **Sky Rueff:** Systems & Electrical Lead
* **Cosme Penney:** OBC & Software Lead
* **Frank Borkowski:** Structural Lead
* **Nicholas Caggiani:** Water Delivery Lead
* **Osvaldo Gonzalez:** Climate Controls Lead
* **Russell Caton:** Testing & Integration Lead
* **Jonathan Ramdhanie:** Finance Lead
