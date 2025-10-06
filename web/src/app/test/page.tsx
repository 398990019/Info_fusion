'use client'

import { MagnifyingGlassIcon, ChartBarIcon, BookOpenIcon } from '@heroicons/react/24/outline'

export default function TestPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-4 text-center">Tailwind CSS 测试页面</h1>
        
        {/* 测试基本样式 */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-semibold mb-4">基本样式测试</h2>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">如果你能看到这个样式正常的页面，说明Tailwind CSS正在工作。</p>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span className="text-sm">蓝色方块</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-sm">绿色方块</span>
            </div>
          </div>
        </div>

        {/* 测试图标 */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-semibold mb-4">图标测试</h2>
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <BookOpenIcon className="w-4 h-4 text-blue-600" />
              <span className="text-sm">小图标 (16px)</span>
            </div>
            <div className="flex items-center space-x-2">
              <ChartBarIcon className="w-6 h-6 text-green-600" />
              <span className="text-sm">中等图标 (24px)</span>
            </div>
            <div className="flex items-center space-x-2">
              <MagnifyingGlassIcon className="w-8 h-8 text-purple-600" />
              <span className="text-sm">大图标 (32px)</span>
            </div>
          </div>
        </div>

        {/* 测试响应式 */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">响应式测试</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-blue-100 p-4 rounded text-center">
              <div className="block sm:hidden">📱 手机</div>
              <div className="hidden sm:block lg:hidden">� 平板</div>
              <div className="hidden lg:block">🖥️ 桌面</div>
            </div>
            <div className="bg-green-100 p-4 rounded text-center">
              <span className="text-sm">网格项目 2</span>
            </div>
            <div className="bg-purple-100 p-4 rounded text-center">
              <span className="text-sm">网格项目 3</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}