module.exports = {
  apps: [
    {
      name: 'gargoyle-packy-bot',
      script: 'src/bot/index.js',
      interpreter: 'node',
      env: {
        NODE_ENV: 'production',
        BOT_MODE: 'microservice'
      },
      max_memory_restart: '200M',
      error_file: 'logs/bot-error.log',
      out_file: 'logs/bot-out.log',
      autorestart: true,
      restart_delay: 3000
    },
    {
      name: 'gargoyle-packy-cognition',
      script: 'src/orchestration/packy_endpoint.py',
      interpreter: 'python3',
      env: {
        PYTHONPATH: '.'
      },
      max_memory_restart: '300M',
      error_file: 'logs/cognition-error.log',
      out_file: 'logs/cognition-out.log',
      autorestart: true,
      restart_delay: 3000
    }
  ]
};
