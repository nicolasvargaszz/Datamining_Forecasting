🚀 Web App de Análisis y Forecasting de Ventas 📊
¡Bienvenido al repositorio de una poderosa herramienta de Data Mining y Forecasting para análisis de ventas en la industria agrícola! 🌾🐄🐖🐓
Esta aplicación utiliza Flask, SQLAlchemy y Facebook Prophet para predecir ventas y analizar materiales necesarios en el futuro. Además, presenta una interfaz web interactiva para la visualización de datos históricos y proyecciones.
🌟 Características Principales
✅ Carga y almacenamiento de datos históricos de ventas en una base de datos SQLite.
✅ Forecasting de ventas utilizando el modelo Prophet para predecir unidades vendidas.
✅ Cálculo automatizado de materiales necesarios (alimentos y recursos) por animal.
✅ Interfaz web interactiva con visualización dinámica de gráficos y datos.
✅ Endpoints REST que devuelven datos en formato JSON para facilitar integraciones.
🛠️ Tecnologías Utilizadas
Backend: Flask + SQLAlchemy + SQLite
Ciencia de Datos: Facebook Prophet + Pandas
Frontend: HTML5 + CSS3 (templates: index.html, forecasting.html, materials.html)
Visualización: Gráficos interactivos embebidos en la web
📂 Estructura del Proyecto
Code
📦 Proyecto
├── .venv/                           # Entorno virtual
├── templates/                       # Archivos HTML
│   ├── index.html                   # Página principal
│   ├── forecasting.html             # Visualización de pronósticos
│   └── materials.html               # Visualización de materiales necesarios
├── Supermix_Sales_data.csv           # Datos históricos de ventas
├── Combined_Sales_Data_forecast.csv  # Resultados de forecasting
├── app.py                            # Código principal de la aplicación
├── knn_model.pkl                     # Modelo KNN (opcional)
├── requirements.txt                  # Librerías necesarias
└── README.md                         # Documentación del proyecto
🚦 Instalación y Ejecución
Clonar el repositorio:
Bash
git clone https://github.com/tu_usuario/tu_proyecto.git
cd tu_proyecto
Configurar el entorno virtual:
Bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
Correr la aplicación:
Bash
python app.py
Abrir en navegador:
http://127.0.0.1:5000 🚀
📈 Cómo Funciona la Aplicación
📥 Cargar Datos
Lee Supermix_Sales_data.csv (datos históricos) y Combined_Sales_Data_forecast.csv (forecast generado por Prophet). Guarda los datos en SQLite. Calcula automáticamente los materiales necesarios por animal.
🖥️ Páginas Interactivas
Página Principal (index.html): Muestra animales y ventas registradas.
Forecasting (forecasting.html): Visualización de predicciones de ventas y ganancias.
Materiales (materials.html): Resumen de recursos necesarios por animal y mes.
🔗 Endpoints REST
GET /forecast_data/<animal> → Datos de proyección.
GET /data/<animal> → Datos históricos.
GET /materials_data → Detalle de materiales requeridos.
GET /materials_summary_data → Resumen de materiales.
🧩 Ejemplo de Forecasting 📊
Datos de entrada:
Fecha	Predicción (yhat)	Animal
2024-01-01	150 unidades	Cow
2024-01-02	200 unidades	Pig
Proyección final:
Cow: 150 unidades → Ganancia estimada: 7.500.000 Gs
Pig: 200 unidades → Ganancia estimada: 6.000.000 Gs
🎯 Objetivo del Proyecto
Facilitar el análisis predictivo y la planificación de recursos en la industria agrícola, optimizando la gestión de ventas y el suministro de materiales.
🤝 Colaboración
¡Toda contribución es bienvenida! ✨ Siéntete libre de enviar un pull request o abrir issues para reportar errores o sugerir mejoras.
📄 Licencia
Este proyecto está bajo la licencia MIT.
