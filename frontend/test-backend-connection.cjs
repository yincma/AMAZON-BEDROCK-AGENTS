#!/usr/bin/env node

/**
 * 后端连接测试脚本
 * 用于验证前端与 AWS API Gateway 的连接是否正常
 */

const axios = require('axios');
const dotenv = require('dotenv');
const path = require('path');

// 加载环境变量
dotenv.config({ path: path.join(__dirname, '.env') });

const API_BASE_URL = process.env.VITE_API_BASE_URL;
const API_KEY = process.env.VITE_API_KEY;

console.log('========================================');
console.log('AWS API Gateway 连接测试');
console.log('========================================\n');

console.log('配置信息:');
console.log(`API URL: ${API_BASE_URL}`);
console.log(`API Key: ${API_KEY ? '已配置' : '未配置'}\n`);

if (!API_BASE_URL) {
  console.error('❌ 错误: VITE_API_BASE_URL 未配置');
  process.exit(1);
}

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'x-api-key': API_KEY })
  }
});

// 测试函数
async function testEndpoint(name, method, path, data = null) {
  console.log(`\n测试 ${name}...`);
  console.log(`${method.toUpperCase()} ${API_BASE_URL}${path}`);
  
  try {
    const config = {
      method,
      url: path,
      ...(data && { data })
    };
    
    const response = await apiClient.request(config);
    console.log(`✅ 成功 - 状态码: ${response.status}`);
    console.log('响应数据:', JSON.stringify(response.data, null, 2).substring(0, 200));
    return true;
  } catch (error) {
    console.log(`❌ 失败`);
    if (error.response) {
      console.log(`状态码: ${error.response.status}`);
      console.log(`错误信息: ${error.response.data?.message || error.response.statusText}`);
      
      // 特殊处理 403 错误
      if (error.response.status === 403) {
        if (error.response.data?.message?.includes('Missing Authentication Token')) {
          console.log('提示: 需要配置 API 密钥 (x-api-key)');
        } else if (error.response.data?.message?.includes('Forbidden')) {
          console.log('提示: API 密钥无效或没有权限');
        }
      }
    } else if (error.request) {
      console.log('错误: 无法连接到服务器');
      console.log('提示: 请检查 API URL 是否正确，或服务器是否在线');
    } else {
      console.log('错误:', error.message);
    }
    return false;
  }
}

// 主测试流程
async function runTests() {
  console.log('\n开始测试...\n');
  console.log('========================================');
  
  let passCount = 0;
  let totalCount = 0;
  
  // 1. 健康检查
  totalCount++;
  if (await testEndpoint('健康检查', 'get', '/health')) {
    passCount++;
  }
  
  // 2. 就绪检查
  totalCount++;
  if (await testEndpoint('就绪检查', 'get', '/health/ready')) {
    passCount++;
  }
  
  // 3. 获取模板列表
  totalCount++;
  if (await testEndpoint('获取模板列表', 'get', '/templates')) {
    passCount++;
  }
  
  // 4. 获取演示文稿列表
  totalCount++;
  if (await testEndpoint('获取演示文稿列表', 'get', '/presentations')) {
    passCount++;
  }
  
  // 5. 创建演示文稿（测试 POST 请求）
  totalCount++;
  const testPresentationData = {
    title: '测试演示文稿',
    topic: '这是一个测试演示文稿，用于验证 API 连接',
    language: 'zh',
    slide_count: 5,
    style: 'professional'
  };
  
  const createResult = await testEndpoint(
    '创建演示文稿任务',
    'post',
    '/presentations',
    testPresentationData
  );
  
  if (createResult) {
    passCount++;
  }
  
  console.log('\n========================================');
  console.log('测试结果汇总');
  console.log('========================================');
  console.log(`通过: ${passCount}/${totalCount}`);
  console.log(`失败: ${totalCount - passCount}/${totalCount}`);
  
  if (passCount === totalCount) {
    console.log('\n🎉 所有测试通过！前后端连接正常。');
  } else if (passCount > 0) {
    console.log('\n⚠️ 部分测试通过。请检查失败的端点。');
  } else {
    console.log('\n❌ 所有测试失败。请检查：');
    console.log('1. API Gateway 是否已部署');
    console.log('2. API URL 是否正确');
    console.log('3. API 密钥是否有效');
    console.log('4. Lambda 函数是否已部署');
  }
  
  console.log('\n建议：');
  if (!API_KEY) {
    console.log('- 配置 API 密钥 (VITE_API_KEY)');
  }
  console.log('- 确保后端服务已完全部署');
  console.log('- 检查 AWS CloudWatch 日志了解详细错误');
  console.log('- 使用 AWS API Gateway 控制台测试端点');
}

// 运行测试
runTests().catch(error => {
  console.error('\n测试脚本执行失败:', error);
  process.exit(1);
});