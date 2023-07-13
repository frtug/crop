FROM python:3.9

# Set the working directory to /app
WORKDIR /app

# Copy the requirements.txt file
COPY requirements.txt .

# Create and activate a virtual environment
RUN python -m venv env
RUN /bin/bash -c "source env/bin/activate"

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .

#Expose the port
EXPOSE 5000

# Run the do_clean.py script
CMD python do_clean.py && python app.py