# CIS Benchmark Parser and GPO Template Generator

A comprehensive four-module tool for parsing CIS (Center for Internet Security) benchmark PDFs, creating customizable Group Policy Object (GPO) templates, managing policy configurations, and deploying them to offline Windows systems. This project provides both a Python backend API and a React frontend interface for complete end-to-end security benchmark implementation.

## Features

### Module 1: PDF Parsing & Policy Extraction
- **PDF Processing**: Extract text and table data from CIS benchmark PDFs
- **Policy Extraction**: Automatically identify and extract security policy settings
- **Data Processing**: Clean and structure extracted policy data
- **Multiple Format Support**: Handle various CIS benchmark PDF formats

### Module 2: GPO Template Generation
- **Template Creation**: Convert extracted policies into Windows Group Policy templates
- **Format Support**: Generate ADMX/ADML templates for modern Group Policy management
- **Customization**: Modify templates with organization-specific requirements
- **Registry Integration**: Direct registry key mapping for policy settings

### Module 3: Dashboard & Management
- **Web Dashboard**: Modern React frontend for policy management
- **Policy Editor**: Interactive editing of policy settings and values
- **Configuration Management**: Save, load, and version control policy configurations
- **Export Options**: Support for multiple export formats (JSON, CSV, XML)
- **Real-time Updates**: Live policy status and configuration tracking

### Module 4: Deployment & Packaging (NEW)
- **Offline Deployment**: Package policies for air-gapped Windows systems
- **Multiple Formats**: Generate POL, REG, PowerShell, INF, and BAT files
- **LGPO Integration**: Microsoft LGPO.exe integration for professional deployment
- **Automated Scripts**: Self-contained deployment packages with validation
- **Backup & Rollback**: Automated policy backup and restore capabilities
- **Windows Version Support**: Compatible with Windows 10, 11, and Server versions
- **CLI Interface**: Command-line tools for automated deployment workflows

## System Architecture

This is a complete four-module system providing end-to-end CIS compliance management:

1. **PDF Parser** → Extract policies from CIS benchmarks
2. **Template Generator** → Create GPO templates from extracted policies  
3. **Dashboard Manager** → Interactive policy configuration and management
4. **Deployment Manager** → Package and deploy to offline Windows systems

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Module 1:     │───▶│   Module 2:     │───▶│   Module 3:     │───▶│   Module 4:     │
│   PDF Parser    │    │ Template Gen    │    │   Dashboard     │    │   Deployment    │
│                 │    │                 │    │                 │    │                 │
│ • Extract Text  │    │ • Create ADMX   │    │ • Web Interface │    │ • Package GPOs  │
│ • Parse Tables  │    │ • Generate ADML │    │ • Policy Editor │    │ • Offline Deploy│
│ • Clean Data    │    │ • Registry Maps │    │ • Config Mgmt   │    │ • Multi-format  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+
- Windows system for deployment testing (optional)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/your-repo/cis-benchmark-parser.git
cd cis-benchmark-parser
```

#### Backend (Python/FastAPI)

1. Navigate to the backend directory
2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the development server:

```bash
uvicorn main:app --reload
```

The backend API will be available at http://localhost:8000

#### Frontend (React)

1. Navigate to the frontend directory
2. Install dependencies:

```bash
npm install
```

3. Run the development server:

```bash
npm start
```

The frontend will be available at http://localhost:3000

## Usage Guide

### Module 1: PDF Processing
1. Upload CIS benchmark PDF via web interface or API
2. Monitor extraction progress in real-time
3. Review extracted policies and settings
4. Export results in JSON or CSV format

### Module 2: Template Generation
1. Select extracted policies for template creation
2. Customize template settings and organization details
3. Generate ADMX/ADML files for Group Policy management
4. Download templates for deployment

### Module 3: Dashboard Management
1. Access web dashboard at http://localhost:3000
2. Create and manage policy configurations
3. Edit individual policy settings and values
4. Version control and backup configurations
5. Export configurations for deployment

### Module 4: Deployment & Packaging
1. Select policies from dashboard for deployment
2. Choose target Windows versions and formats
3. Configure deployment options (backup, validation, etc.)
4. Generate offline deployment packages
5. Deploy to target systems using included scripts

For detailed deployment instructions, see [DEPLOYMENT.md](backend/deployment/DEPLOYMENT.md)

## API Endpoints

### Module 1: PDF Parsing
- `POST /upload-pdf/`: Upload a PDF for processing
- `GET /status/{task_id}`: Check the status of an extraction task
- `GET /results/{task_id}`: Get the extracted policies
- `GET /download/{task_id}?format=json|csv`: Download the policies

### Module 2: Template Generation
- `POST /create-template/`: Generate GPO templates from policies
- `GET /templates/`: List available templates
- `POST /convert-template/`: Convert templates between formats

### Module 3: Dashboard Management
- `GET /policies/`: List all managed policies
- `POST /policies/`: Create new policy configuration
- `PUT /policies/{id}`: Update policy settings
- `DELETE /policies/{id}`: Delete policy configuration
- `GET /dashboard/stats`: Get dashboard statistics

### Module 4: Deployment & Packaging
- `POST /deployment/packages/`: Create deployment packages
- `GET /deployment/packages/`: List all packages
- `GET /deployment/packages/{id}`: Get package details
- `DELETE /deployment/packages/{id}`: Delete package
- `POST /deployment/packages/{id}/build`: Build deployment package
- `GET /deployment/jobs/{job_id}`: Monitor build progress
- `GET /deployment/packages/{id}/download`: Download built package
- `GET /deployment/windows-versions`: Get supported Windows versions

For complete API documentation:
- Main API docs: http://localhost:8000/docs
- Deployment module docs: [DEPLOYMENT.md](backend/deployment/DEPLOYMENT.md)

## Command Line Interface

### Deployment CLI
The deployment module includes a comprehensive CLI for automated workflows:

```bash
# Interactive package creation
python backend/deployment_cli.py

# Create package programmatically
python backend/create_sample_packages.py
```

### Key CLI Features
- Interactive policy selection
- Automated package creation
- Job monitoring and status updates
- Package management and cleanup
- Export format selection

## Architecture Details

### Backend Components

- **PDF Parser**: Uses PyPDF2, pdfminer.six, and camelot-py to extract text and tables
- **Policy Extractor**: Identifies and extracts policy settings using pattern matching
- **Template Generator**: Creates ADMX/ADML files from extracted policies
- **Dashboard Manager**: Handles policy configuration and management
- **Deployment Manager**: Packages policies for offline deployment
- **LGPO Integration**: Microsoft LGPO.exe wrapper for professional deployment
- **FastAPI Server**: Provides REST API endpoints for all modules

### Frontend Components

- **React SPA**: Single-page application built with React
- **Material UI**: Component library for modern UI design
- **Policy Dashboard**: Interactive policy management interface
- **Deployment Interface**: Package creation and download UI
- **PWA Features**: Service worker for offline capabilities
- **Responsive Design**: Works on desktop and mobile devices

### Deployment Architecture

- **Multi-Format Support**: POL, REG, PS1, INF, BAT file generation
- **Offline Capability**: Self-contained packages with no network dependencies
- **Validation System**: Pre and post-deployment validation
- **Backup Integration**: Automatic policy backup before deployment
- **Rollback Support**: Automated rollback on deployment failure
- **Windows Compatibility**: Support for Windows 10, 11, and Server versions

## File Structure

```
cis-benchmark-parser/
├── backend/
│   ├── deployment/              # Module 4: Deployment & Packaging
│   │   ├── models_deployment.py # Deployment data models
│   │   ├── deployment_manager.py# Core deployment logic
│   │   ├── lgpo_utils.py        # LGPO integration utilities
│   │   └── DEPLOYMENT.md        # Comprehensive deployment docs
│   ├── tools/                   # Helper tools and utilities
│   │   ├── install_lgpo.bat     # LGPO installation helper
│   │   └── README.md            # Tools documentation
│   ├── main.py                  # FastAPI application with all modules
│   ├── deployment_cli.py        # Command-line interface
│   ├── create_sample_packages.py# Sample deployment script
│   ├── pdf_processor.py         # Module 1: PDF parsing
│   ├── policy_extractor.py      # Module 1: Policy extraction
│   ├── template_generator.py    # Module 2: Template generation
│   ├── dashboard_manager.py     # Module 3: Dashboard management
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DeploymentManager.js  # Module 4: Deployment UI
│   │   │   ├── PolicyDashboard.js    # Module 3: Dashboard UI
│   │   │   └── ...                   # Other UI components
│   │   └── App.js               # Main React application
│   ├── package.json             # Node.js dependencies
│   └── public/                  # Static assets
└── README.md                    # This file
```

## License

Open-source under MIT License

## Acknowledgements

This project uses the following open-source libraries:

### Backend Dependencies
- [PyPDF2](https://github.com/py-pdf/PyPDF2) - PDF processing
- [pdfminer.six](https://github.com/pdfminer/pdfminer.six) - Advanced PDF text extraction
- [camelot-py](https://github.com/camelot-dev/camelot) - Table extraction from PDFs
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings management

### Frontend Dependencies
- [React](https://reactjs.org/) - UI framework
- [Material-UI](https://mui.com/) - React component library
- [Axios](https://axios-http.com/) - HTTP client for API communication

### Deployment Tools
- [Microsoft LGPO](https://www.microsoft.com/en-us/download/details.aspx?id=55319) - Local Group Policy Object utility (optional)

A comprehensive four-module tool for parsing CIS (Center for Internet Security) benchmark PDFs, creating customizable Group Policy Object (GPO) templates, managing policy configurations, and deploying them to offline Windows systems. This project provides both a Python backend API and a React frontend interface for complete end-to-end security benchmark implementation.

## Features

### Module 1: PDF Parsing & Policy Extraction
- **PDF Processing**: Extract text and table data from CIS benchmark PDFs
- **Policy Extraction**: Automatically identify and extract security policy settings
- **Data Processing**: Clean and structure extracted policy data

### Module 2: GPO Template Generation
- **Template Creation**: Convert extracted policies into Windows Group Policy templates
- **Format Support**: Generate ADMX/ADML templates for modern Group Policy management
- **Customization**: Modify templates with organization-specific requirements

### Module 3: Dashboard & Management
- **Web Dashboard**: Modern React frontend for policy management
- **Policy Editor**: Interactive editing of policy settings and values
- **Configuration Management**: Save, load, and version control policy configurations
- **Export Options**: Support for multiple export formats (JSON, CSV, XML)

### Module 4: Deployment & Packaging
- **Offline Deployment**: Package policies for air-gapped Windows systems
- **Multiple Formats**: Generate POL, REG, PowerShell, INF, and BAT files
- **LGPO Integration**: Microsoft LGPO.exe integration for professional deployment
- **Automated Scripts**: Self-contained deployment packages with validation
- **Backup & Rollback**: Automated policy backup and restore capabilities

## System Architecture

This is a complete four-module system providing end-to-end CIS compliance management:

1. **PDF Parser** → Extract policies from CIS benchmarks
2. **Template Generator** → Create GPO templates from extracted policies
3. **Dashboard Manager** → Interactive policy configuration and management
4. **Deployment Manager** → Package and deploy to offline Windows systems

## Quick Start