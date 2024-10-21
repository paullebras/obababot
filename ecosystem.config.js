module.exports = {
  apps: [
    {
      name: "obababot",
      script: "main.py",
      interpreter: "./venv/bin/python", // Use Python from the virtual environment
      instances: 1, // Number of instances (0 for max instances)
      autorestart: true, // Automatically restart if the process crashes
      watch: false, // Set to true if you want to enable watching file changes
      max_memory_restart: "500M", // Restart if the app exceeds 500MB of memory usage
      env: {
        PYTHON_ENV: "production",
      },
    },
  ],
};
