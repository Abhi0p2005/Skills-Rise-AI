import logging

logger = logging.getLogger("gigpilot_db")

workers = {}
worker_progress = {}

courses = {
    "solar panel installation": {
        "micro_lessons": [
            "Understand basic photovoltaic (PV) cell principles",
            "Learn mounting and racking system installation",
            "Practice DC/AC wiring and inverter connections",
            "Study rooftop safety harness and fall-protection protocol"
        ],
        "difficulty": "medium",
        "questions": [
            {
                "question": "What is the primary function of a photovoltaic (PV) cell?",
                "options": [
                    "Convert sunlight directly into electricity",
                    "Store solar energy as heat",
                    "Convert wind energy into electricity",
                    "Regulate voltage in a solar system"
                ],
                "correct_index": 0,
                "explanation": "PV cells convert sunlight directly into electricity via the photovoltaic effect."
            },
            {
                "question": "What safety equipment is mandatory before working on a rooftop solar installation?",
                "options": [
                    "Fall-protection harness anchored to a secure point",
                    "Welding goggles and gloves",
                    "Respirator mask",
                    "Fire extinguisher"
                ],
                "correct_index": 0,
                "explanation": "A fall-protection harness anchored to a secure point is mandatory to prevent falls from heights."
            },
            {
                "question": "What type of current do solar panels produce?",
                "options": [
                    "Alternating Current (AC)",
                    "Direct Current (DC)",
                    "Pulsed Current",
                    "Radio Frequency Current"
                ],
                "correct_index": 1,
                "explanation": "Solar panels produce Direct Current (DC), which is then converted to AC by an inverter."
            },
            {
                "question": "What is the purpose of a solar inverter?",
                "options": [
                    "Convert DC from panels to AC for home use",
                    "Increase the voltage of solar panels",
                    "Store excess solar energy",
                    "Protect panels from lightning strikes"
                ],
                "correct_index": 0,
                "explanation": "The inverter converts the DC electricity from solar panels into AC electricity used by home appliances."
            },
            {
                "question": "Which mounting type is most common for residential rooftop solar?",
                "options": [
                    "Rail-based racking system",
                    "Ground-mounted tracking system",
                    "Pole-mounted system",
                    "Floating platform system"
                ],
                "correct_index": 0,
                "explanation": "Rail-based racking systems are most common for residential rooftops due to their versatility and strength."
            },
            {
                "question": "What does a charge controller do in a solar system with batteries?",
                "options": [
                    "Prevents battery overcharging and deep discharge",
                    "Converts DC to AC",
                    "Monitors sunlight intensity",
                    "Disconnects panels during rain"
                ],
                "correct_index": 0,
                "explanation": "A charge controller regulates voltage/current to prevent battery overcharging and deep discharge."
            },
            {
                "question": "What is net metering?",
                "options": [
                    "Billing mechanism that credits solar owners for excess power sent to grid",
                    "A method to measure panel efficiency",
                    "A safety inspection standard",
                    "A government subsidy calculation"
                ],
                "correct_index": 0,
                "explanation": "Net metering credits solar system owners for the excess electricity they feed back into the grid."
            }
        ]
    },
    "electrical wiring": {
        "micro_lessons": [
            "Learn color-coding standards for residential wiring",
            "Practice safe circuit breaker isolation (lock-out/tag-out)",
            "Understand load calculation basics"
        ],
        "difficulty": "easy",
        "questions": [
            {
                "question": "What is the first step before touching any wiring in a panel?",
                "options": [
                    "Isolate and lock out the circuit breaker",
                    "Wear rubber gloves",
                    "Test voltage with a multimeter",
                    "Call a supervisor"
                ],
                "correct_index": 0,
                "explanation": "Always isolate and lock out the circuit breaker to ensure zero current flow before working."
            },
            {
                "question": "What color wire is used for the ground (earth) connection in most countries?",
                "options": [
                    "Green or bare copper",
                    "Red",
                    "Black",
                    "White"
                ],
                "correct_index": 0,
                "explanation": "Green (or bare copper) is the universal color code for ground/earth wires."
            },
            {
                "question": "What does a circuit breaker do?",
                "options": [
                    "Automatically cuts power when current exceeds safe limit",
                    "Converts AC to DC",
                    "Regulates voltage",
                    "Stores electricity"
                ],
                "correct_index": 0,
                "explanation": "A circuit breaker automatically interrupts current flow when it exceeds safe limits, preventing fire."
            },
            {
                "question": "What is the standard voltage for household outlets in India?",
                "options": [
                    "230V",
                    "110V",
                    "440V",
                    "12V"
                ],
                "correct_index": 0,
                "explanation": "India uses 230V at 50Hz for standard household electrical outlets."
            },
            {
                "question": "Which tool is used to measure electrical current without touching wires?",
                "options": [
                    "Clamp meter",
                    "Multimeter with probes",
                    "Voltage tester pen",
                    "Insulation tester"
                ],
                "correct_index": 0,
                "explanation": "A clamp meter measures current flowing through a conductor without direct electrical contact."
            }
        ]
    },
    "plumbing": {
        "micro_lessons": [
            "Learn pipe-fitting and sealing techniques",
            "Understand water pressure testing",
            "Practice leak detection methods"
        ],
        "difficulty": "easy",
        "questions": [
            {
                "question": "What tool is used to detect a hidden pipe leak?",
                "options": [
                    "Pressure gauge or moisture meter",
                    "Thermal camera",
                    "Stethoscope",
                    "Endoscope"
                ],
                "correct_index": 0,
                "explanation": "A pressure gauge (drop indicates leak) or moisture meter detects hidden pipe leaks."
            },
            {
                "question": "What is the most common material for modern water supply pipes?",
                "options": [
                    "PVC (Polyvinyl Chloride)",
                    "Galvanized Iron",
                    "Lead",
                    "Concrete"
                ],
                "correct_index": 0,
                "explanation": "PVC is the most common modern material due to its corrosion resistance, low cost, and ease of installation."
            },
            {
                "question": "What is the purpose of a P-trap under a sink?",
                "options": [
                    "Prevent sewer gases from entering the building",
                    "Increase water pressure",
                    "Filter debris from water",
                    "Reduce pipe noise"
                ],
                "correct_index": 0,
                "explanation": "The P-trap holds water that creates a seal, preventing sewer gases from entering the building."
            },
            {
                "question": "What should be applied to threaded pipe joints to prevent leaks?",
                "options": [
                    "PTFE tape (plumber's tape)",
                    "Super glue",
                    "Silicone caulk",
                    "Epoxy resin"
                ],
                "correct_index": 0,
                "explanation": "PTFE tape (teflon tape) is wrapped around threaded pipe joints to create a watertight seal."
            },
            {
                "question": "What does a pressure reducing valve (PRV) do?",
                "options": [
                    "Lowers incoming water pressure to a safe level",
                    "Increases water pressure for showers",
                    "Shuts off water during earthquakes",
                    "Prevents backflow contamination"
                ],
                "correct_index": 0,
                "explanation": "A PRV reduces high incoming main water pressure to a safe, consistent level for the building."
            }
        ]
    },
    "hvac repair": {
        "micro_lessons": [
            "Understand refrigerant handling regulations",
            "Learn compressor diagnostics basics",
            "Practice safe gas cylinder handling"
        ],
        "difficulty": "medium",
        "questions": [
            {
                "question": "Why must refrigerant handling be certified?",
                "options": [
                    "Because refrigerants are regulated substances that can harm health/environment if mishandled",
                    "Because it requires heavy machinery",
                    "Because only engineers are allowed",
                    "Because refrigerants are flammable"
                ],
                "correct_index": 0,
                "explanation": "Refrigerants are regulated under environmental laws (e.g., Montreal Protocol) due to their ozone-depleting and global warming potential."
            },
            {
                "question": "What does a compressor do in an AC system?",
                "options": [
                    "Compresses refrigerant gas, raising its temperature and pressure",
                    "Filters dust from the air",
                    "Circulates cool water",
                    "Controls the thermostat"
                ],
                "correct_index": 0,
                "explanation": "The compressor pressurizes refrigerant gas, which is essential for the heat exchange cycle."
            },
            {
                "question": "What is the function of an expansion valve in an HVAC system?",
                "options": [
                    "Reduces refrigerant pressure to cool it before the evaporator",
                    "Expands the ductwork",
                    "Increases compressor speed",
                    "Filters out moisture"
                ],
                "correct_index": 0,
                "explanation": "The expansion valve causes a sudden pressure drop, cooling the refrigerant before it enters the evaporator."
            },
            {
                "question": "What does HVAC stand for?",
                "options": [
                    "Heating, Ventilation, and Air Conditioning",
                    "High Voltage Air Circulation",
                    "Heat Vacuum Air Control",
                    "Home Ventilation and Cooling"
                ],
                "correct_index": 0,
                "explanation": "HVAC stands for Heating, Ventilation, and Air Conditioning."
            },
            {
                "question": "Which gas is commonly used as a refrigerant in modern split ACs?",
                "options": [
                    "R-32",
                    "Oxygen",
                    "Nitrogen",
                    "Hydrogen"
                ],
                "correct_index": 0,
                "explanation": "R-32 is a modern, more environmentally-friendly refrigerant commonly used in split AC systems."
            },
            {
                "question": "What is the purpose of a capacitor in an AC unit?",
                "options": [
                    "Provides a high-voltage boost to start the compressor and fan motors",
                    "Stores refrigerant",
                    "Filters air impurities",
                    "Regulates room temperature"
                ],
                "correct_index": 0,
                "explanation": "Capacitors store electrical charge and release it to start the compressor and fan motors."
            },
            {
                "question": "Why should HVAC technicians wear PPE when handling refrigerants?",
                "options": [
                    "To prevent frostbite and chemical burns from pressurized refrigerant",
                    "To look professional",
                    "To avoid dust inhalation",
                    "To comply with uniform policy"
                ],
                "correct_index": 0,
                "explanation": "Pressurized refrigerants can cause severe frostbite or chemical burns on contact with skin or eyes."
            }
        ]
    },
    "semiconductor manufacturing": {
        "micro_lessons": [
            "Understand cleanroom protocols and contamination control (Class 10/100/1000)",
            "Learn wafer fabrication process: oxidation, photolithography, etching, doping",
            "Practice equipment handling: wafer sorters, die bonders, wire bonders",
            "Study quality inspection using microscopes and automated optical inspection (AOI)"
        ],
        "difficulty": "hard",
        "questions": [
            {
                "question": "What is the most critical contamination control requirement in a semiconductor cleanroom?",
                "options": [
                    "HEPA/ULPA filtered airflow, full cleanroom gowning, and strict particle count monitoring",
                    "Regular mopping of floors",
                    "Opening windows for ventilation",
                    "Using standard room fans"
                ],
                "correct_index": 0,
                "explanation": "Cleanrooms use HEPA/ULPA filters to maintain strict particle counts (Class 10 = 10 particles/ft³ max). Full gowning prevents human contamination."
            },
            {
                "question": "What does a stepper do in semiconductor manufacturing?",
                "options": [
                    "Projects circuit patterns onto a wafer using UV light through a reticle",
                    "Cuts wafers into individual chips",
                    "Bonds wires to the chip package",
                    "Tests the electrical properties of chips"
                ],
                "correct_index": 0,
                "explanation": "A stepper is a photolithography tool that projects the chip design onto the wafer layer by layer."
            },
            {
                "question": "What is the purpose of the photolithography step in wafer fabrication?",
                "options": [
                    "Transfer circuit patterns onto the wafer surface using light-sensitive photoresist",
                    "Clean the wafer with chemicals",
                    "Test the electrical conductivity",
                    "Package the finished chips"
                ],
                "correct_index": 0,
                "explanation": "Photolithography uses UV light to transfer circuit patterns from a mask to a photoresist-coated wafer."
            },
            {
                "question": "What does CMP (Chemical Mechanical Planarization) do?",
                "options": [
                    "Flattens and polishes wafer surfaces using chemical slurry and mechanical abrasion",
                    "Cuts wafers into individual die",
                    "Deposits metal layers on the wafer",
                    "Dopes silicon with impurities"
                ],
                "correct_index": 0,
                "explanation": "CMP uses a combination of chemical etching and mechanical polishing to create ultra-flat wafer surfaces."
            },
            {
                "question": "What is a wafer?",
                "options": [
                    "A thin slice of semiconductor material (usually silicon) on which chips are fabricated",
                    "A tool for cutting metal",
                    "A type of cleaning cloth",
                    "A packaging material for chips"
                ],
                "correct_index": 0,
                "explanation": "A wafer is a thin slice of crystalline silicon used as the substrate for semiconductor device fabrication."
            },
            {
                "question": "What does a die bonder do?",
                "options": [
                    "Attaches individual semiconductor die to a package substrate using epoxy or solder",
                    "Tests the electrical performance of chips",
                    "Prints labels on packages",
                    "Inspects wafers for defects"
                ],
                "correct_index": 0,
                "explanation": "Die bonding is the process of attaching the semiconductor chip to its package using adhesive or solder."
            },
            {
                "question": "What is doping in semiconductor manufacturing?",
                "options": [
                    "Adding impurities to silicon to modify its electrical properties (N-type or P-type)",
                    "Cleaning wafers with chemicals",
                    "Coating wafers with photoresist",
                    "Cutting wafers into individual chips"
                ],
                "correct_index": 0,
                "explanation": "Doping introduces specific impurities (e.g., boron for P-type, phosphorus for N-type) to control conductivity."
            },
            {
                "question": "What class of cleanroom allows a maximum of 100 particles (0.5 micron) per cubic foot?",
                "options": [
                    "Class 100",
                    "Class 10",
                    "Class 1000",
                    "Class 1"
                ],
                "correct_index": 0,
                "explanation": "Class 100 cleanroom allows max 100 particles (>=0.5 microns) per cubic foot of air."
            },
            {
                "question": "What type of packaging is used for protecting semiconductor chips during shipping?",
                "options": [
                    "Anti-static trays, tubes, or tape-and-reel packaging",
                    "Cardboard boxes with bubble wrap",
                    "Plastic bags",
                    "Metal containers"
                ],
                "correct_index": 0,
                "explanation": "Semiconductor chips are shipped in ESD-safe (electrostatic discharge safe) packaging to prevent damage."
            },
            {
                "question": "What is the typical yield rate considered good in semiconductor manufacturing?",
                "options": [
                    "Above 90% (functional chips out of total manufactured)",
                    "50%",
                    "Below 30%",
                    "100% is standard"
                ],
                "correct_index": 0,
                "explanation": "A yield above 90% is considered excellent in semiconductor manufacturing. 100% is nearly impossible due to defects."
            }
        ]
    },
    "cnc machining": {
        "micro_lessons": [
            "Understand CNC machine types: milling, lathe, routing, plasma cutting",
            "Learn G-code programming basics and toolpath generation",
            "Practice setup: workpiece clamping, tool offset calibration, spindle speed selection",
            "Study quality control using calipers, micrometers, and CMM inspection"
        ],
        "difficulty": "medium",
        "questions": [
            {
                "question": "What does the G-code G00 command do?",
                "options": [
                    "Rapid positioning (fast movement without cutting)",
                    "Linear cutting movement",
                    "Circular interpolation clockwise",
                    "Tool change"
                ],
                "correct_index": 0,
                "explanation": "G00 is a non-cutting rapid positioning command that moves the tool at maximum speed."
            },
            {
                "question": "What does M06 G-code command typically do?",
                "options": [
                    "Tool change - stops spindle and moves to tool change position",
                    "Starts spindle rotation",
                    "Ends the program",
                    "Activates coolant"
                ],
                "correct_index": 0,
                "explanation": "M06 halts spindle rotation and positions the machine for a manual or automatic tool change."
            },
            {
                "question": "What is the purpose of coolant in CNC machining?",
                "options": [
                    "Lubricate and cool the cutting tool/workpiece, extending tool life",
                    "Clean the machine after operation",
                    "Power the hydraulic systems",
                    "Lubricate the machine导轨"
                ],
                "correct_index": 0,
                "explanation": "Coolant reduces friction heat at the cutting interface, prevents thermal damage, and extends tool life."
            },
            {
                "question": "What is the difference between CNC milling and CNC turning?",
                "options": [
                    "Milling: rotating tool cuts stationary workpiece. Turning: rotating workpiece is cut by stationary tool",
                    "Milling is for metal only, turning is for wood",
                    "There is no difference",
                    "Turning uses lasers, milling uses blades"
                ],
                "correct_index": 0,
                "explanation": "In milling the tool rotates; in turning (lathe) the workpiece rotates against a stationary cutting tool."
            },
            {
                "question": "What tool is used to measure the diameter of a machined shaft with high precision?",
                "options": [
                    "Micrometer",
                    "Ruler",
                    "Tape measure",
                    "Vernier caliper (typically less precise than micrometer)"
                ],
                "correct_index": 0,
                "explanation": "A micrometer measures shaft diameters with accuracy up to 0.001mm, far more precise than a ruler or caliper."
            },
            {
                "question": "What is the purpose of a tool offset in CNC machining?",
                "options": [
                    "Compensates for the exact length and diameter of each cutting tool",
                    "Moves the tool to a parking position",
                    "Changes the cutting speed",
                    "Selects the type of material"
                ],
                "correct_index": 0,
                "explanation": "Tool offsets account for variations in tool geometry, ensuring cuts are accurate to the programmed dimensions."
            },
            {
                "question": "What does spindle speed (RPM) affect in machining?",
                "options": [
                    "Cutting efficiency, surface finish, and tool wear rate",
                    "Only the noise level",
                    "Only the color of the material",
                    "The weight of the workpiece"
                ],
                "correct_index": 0,
                "explanation": "RPM directly affects cutting speed, which influences surface finish quality, heat generation, and tool life."
            }
        ]
    },
    "automation & plc": {
        "micro_lessons": [
            "Understand PLC architecture: CPU, I/O modules, power supply, programming ports",
            "Learn ladder logic programming basics: rungs, contacts, coils, timers, counters",
            "Practice wiring sensors (proximity, photoelectric) and actuators (solenoids, motors)",
            "Study SCADA basics and HMI panel configuration for industrial monitoring"
        ],
        "difficulty": "hard",
        "questions": [
            {
                "question": "What is the difference between a normally open (NO) and normally closed (NC) contact in ladder logic?",
                "options": [
                    "NO contact closes (passes current) when energized; NC contact opens (blocks current) when energized",
                    "NO is for high voltage, NC is for low voltage",
                    "There is no difference",
                    "NO contacts are always closed"
                ],
                "correct_index": 0,
                "explanation": "In ladder logic, NO contacts pass current when the input is activated; NC contacts pass current when the input is NOT activated."
            },
            {
                "question": "What does PLC stand for?",
                "options": [
                    "Programmable Logic Controller",
                    "Power Line Controller",
                    "Primary Logic Circuit",
                    "Programmable Load Connector"
                ],
                "correct_index": 0,
                "explanation": "PLC stands for Programmable Logic Controller - an industrial computer used to automate manufacturing processes."
            },
            {
                "question": "What type of sensor detects nearby objects without physical contact using a magnetic field?",
                "options": [
                    "Inductive proximity sensor",
                    "Photoelectric sensor",
                    "Thermocouple",
                    "Pressure sensor"
                ],
                "correct_index": 0,
                "explanation": "Inductive proximity sensors detect metal objects using electromagnetic fields without physical contact."
            },
            {
                "question": "What is SCADA?",
                "options": [
                    "Supervisory Control and Data Acquisition - a system for monitoring and controlling industrial processes",
                    "A type of PLC programming language",
                    "A safety certification standard",
                    "A type of electric motor"
                ],
                "correct_index": 0,
                "explanation": "SCADA systems provide centralized monitoring and control of industrial processes across large areas."
            },
            {
                "question": "What does a timer ON-delay (TON) instruction do in ladder logic?",
                "options": [
                    "Delays turning ON the output for a set time after the input is activated",
                    "Turns ON the output immediately and delays turning it OFF",
                    "Counts the number of times an input is activated",
                    "Resets all other timers"
                ],
                "correct_index": 0,
                "explanation": "TON delays the activation of the output by a set time (preset value) after the input condition becomes true."
            },
            {
                "question": "What is the function of an HMI (Human Machine Interface)?",
                "options": [
                    "Provides a visual touchscreen interface for operators to monitor and control machines",
                    "Wires sensors to the PLC",
                    "Converts analog signals to digital",
                    "Supplies power to the PLC"
                ],
                "correct_index": 0,
                "explanation": "An HMI displays machine status and allows operators to input commands through a graphical touchscreen."
            },
            {
                "question": "Which communication protocol is commonly used for industrial automation between PLCs and field devices?",
                "options": [
                    "PROFIBUS or Modbus",
                    "USB",
                    "Bluetooth",
                    "WiFi"
                ],
                "correct_index": 0,
                "explanation": "PROFIBUS and Modbus are industry-standard industrial communication protocols for PLCs and field devices."
            },
            {
                "question": "What is a relay in an automation system?",
                "options": [
                    "An electrically operated switch that uses a low-power signal to control a high-power circuit",
                    "A type of sensor",
                    "A programming language for PLCs",
                    "A power supply unit"
                ],
                "correct_index": 0,
                "explanation": "A relay allows a low-voltage PLC output to switch high-voltage devices like motors and heaters safely."
            },
            {
                "question": "What does a counter up (CTU) instruction do in PLC ladder logic?",
                "options": [
                    "Increments a count value each time the input transitions from OFF to ON",
                    "Counts down from a preset value",
                    "Measures the time between events",
                    "Resets the accumulator"
                ],
                "correct_index": 0,
                "explanation": "CTU counts the number of times an input changes from 0 to 1 (rising edge) and activates output when preset is reached."
            }
        ]
    }
}
