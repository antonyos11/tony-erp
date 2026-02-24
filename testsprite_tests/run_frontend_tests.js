const { spawn } = require('child_process');
const path = require('path');

console.log('🚀 بدء اختبارات الواجهة الأمامية لنظام Tony ERP...\n');

const testsprite = spawn('node', [
  path.join(process.env.HOME, '.npm/_npx/8ddf6bea01b2519d/node_modules/@testsprite/testsprite-mcp/dist/index.js'),
  'generateCodeAndExecute'
], {
  cwd: '/var/www/tony_erp',
  env: {
    ...process.env,
    PROJECT_PATH: '/var/www/tony_erp',
    TEST_IDS: '[]',
    ADDITIONAL_INSTRUCTION: 'اختبر جميع الصفحات والأزرار والمعادلات الحسابية في النظام'
  }
});

testsprite.stdout.on('data', (data) => {
  console.log(data.toString());
});

testsprite.stderr.on('data', (data) => {
  console.error(data.toString());
});

testsprite.on('close', (code) => {
  console.log(`\n✅ الاختبارات انتهت بكود: ${code}`);
  process.exit(code);
});
