# 🧠 scraping-precios

## 📋 Descripción del proyecto  
Este proyecto automatiza la **extracción, análisis y notificación diaria de precios** de productos deportivos (como proteínas y creatina) desde la web [HSNstore](https://www.hsnstore.com).

Cada día el script:
1. **Realiza web scraping** con *Playwright* para obtener el precio actual de varios productos.  
2. **Guarda los datos históricos** en archivos `.xlsx` y `.csv`.  
3. **Genera gráficas automáticas** de la evolución de precios.  
4. **Envía un correo electrónico** con los precios del día y las gráficas adjuntas, avisando si hay un **mínimo o máximo histórico**.

En resumen, es una herramienta completa de **monitorización automática de precios**.

---

## ⚙️ Estructura del proyecto
```
scraping-precios/
│
├── main.py              # Script principal que ejecuta todo el flujo
├── scraper.py           # Función que realiza el scraping con Playwright
├── plotter.py           # Genera gráficas de evolución de precios
├── mailer.py            # Envía correos con precios y gráficas
├── visualizacion.py     # Alternativa simplificada para graficar precios
│
├── data/                # Carpeta de salida: CSV, XLSX y PNG
│
├── .env                 # Credenciales (EMAIL_USER, EMAIL_PASS)
├── requeriments.txt     # Dependencias del proyecto
└── README.md            # Este archivo
```

---

## 🧰 Tecnologías utilizadas

- **Python 3.9+**  
- **Playwright** – automatización de navegador para scraping.  
- **Pandas** – manejo de datos históricos.  
- **Matplotlib / Seaborn** – visualización de precios.  
- **smtplib / EmailMessage** – envío de correos con adjuntos.  
- **dotenv** – manejo de credenciales mediante archivo `.env`.

---

## 🚀 Instalación y configuración

### 1. Clona el repositorio
```bash
git clone https://github.com/sergiosgd01/scraping-precios.git
cd scraping-precios
```

### 2. Crea un entorno virtual (opcional)
```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

### 3. Instala las dependencias
```bash
pip install -r requeriments.txt
```

### 4. Configura las variables de entorno
Crea un archivo `.env` en la raíz del proyecto con tus credenciales de Gmail:
```env
EMAIL_USER=tu_correo@gmail.com
EMAIL_PASS=tu_contraseña_o_app_password
```

### 5. Ejecuta el script principal
```bash
python main.py
```

---

## 🧩 Flujo de funcionamiento

### 1️⃣ Extracción de datos – `scraper.py`
Usa Playwright para:
- Abrir la página del producto.
- Aceptar cookies automáticamente.
- Seleccionar la variante del producto (peso).
- Extraer nombre, peso y precio.
- Guardar los datos en `data/precios_<producto>.xlsx` y `.csv`.

### 2️⃣ Generación de gráficas – `plotter.py`
Convierte el histórico en una gráfica diaria de precios:
- Resalta los precios máximo y mínimo.
- Guarda las gráficas como `.png` dentro de `data/`.

### 3️⃣ Envío de correo – `mailer.py`
- Lee los precios del día y los compara con el histórico.
- Agrega avisos automáticos:
  - 🎉 "¡PRECIO MÁS BAJO HISTÓRICO!"
  - ⚠️ "PRECIO MÁS ALTO HISTÓRICO"
- Adjunta las gráficas (`.png`) y envía un correo con formato HTML.

### 4️⃣ Automatización general – `main.py`
El script principal:
- Define los productos y selectores CSS.
- Llama a `scrape_producto()`, `graficar_precios()` y `enviar_email()`.
- Puede programarse fácilmente con un **cron job** o **Windows Task Scheduler**.

---

## 📊 Ejemplo de salida

**Correo enviado:**
```
Precios de hoy (2025-10-28):
- Creatina (1Kg): 29,90 € 🎉 ¡PRECIO MÁS BAJO HISTÓRICO!
- Proteína (2Kg): 49,90 €
- Proteína pack (5x500g): 125,00 € ⚠️ PRECIO MÁS ALTO HISTÓRICO ⚠️
```

**Adjuntos:**
- 📈 `creatina.png`
- 📈 `evowhey.png`
- 📈 `proteina_pack.png`

---

## 💡 Posibles mejoras futuras

- Agregar soporte para más tiendas y productos.
- Añadir almacenamiento en base de datos (SQLite o PostgreSQL).
- Integrar un panel web de visualización.
- Automatizar ejecución diaria en la nube (AWS Lambda, GitHub Actions, etc.).

---

## 🛡️ Licencia

Este proyecto está licenciado bajo la **MIT License**.
```
MIT License

Copyright (c) 2025 Sergio Guijarro

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👨‍💻 Autor

Desarrollado por **Sergio Guijarro** ([@sergiosgd01](https://github.com/sergiosgd01))  
📧 sergiosgd2001@gmail.com
