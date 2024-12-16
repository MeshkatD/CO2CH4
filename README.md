# CO2CH4: Superstructure Optimisation for DAC & Utilisation to CH4

## Overview
This project contains a Pyomo-based optimisation model (version 15) designed for analysing and optimising a system that integrates:
- Direct Air Capture (DAC) for CO2
- Electrolysers (AEL, SOEL, PEMEL)
- Methanation reactors with Dual Function Materials (DFM)
- Temperature-Vacuum Swing Adsorption (TVSA)
- Ancillary systems like fans, steam generation, air coolers, and separators.

The model is configured to evaluate and optimise economic and operational metrics such as Total Annualised Cost (TAC) and system profit under variable conditions like electricity prices and sorbent costs.

## Features
- **Integrated Systems**: Includes DAC, electrolysers, DFM reactors, TVSA units, and more.
- **Flexible Inputs**: Adjustable parameters for CO2 and methane production rates, equipment configurations, and material properties.
- **Economic Optimisation**: Computes CAPEX, OPEX, and TAC for various configurations.
- **Thermodynamic Modelling**: Incorporates thermophysical properties and chemical kinetics of solid sorbents.
- **Sensitivity Analysis**: Configured for sensitivity studies on key parameters.

## File Structure
- **`CO2CH4-00.py`**: Main Python script with the optimisation model.
- **`project_database.xlsx`**: Data source for steam table and other operational parameters.
- **Output Files**: Automatically generated reports and results (e.g., TAC and profit metrics).

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/MeshkatD/CO2CH4.git
   cd CO2CH4
