export default function SimpleTest() {
  return (
    <div style={{
      padding: '20px',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: '#f0f0f0',
      minHeight: '100vh'
    }}>
      <h1 style={{
        color: '#333',
        fontSize: '24px',
        marginBottom: '20px'
      }}>
        简单测试页面（使用内联样式）
      </h1>
      
      <div style={{
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <h2 style={{ color: '#666', fontSize: '18px', marginBottom: '10px' }}>
          基础HTML测试
        </h2>
        <p style={{ color: '#888', fontSize: '14px' }}>
          如果你能正常看到这个页面，说明Next.js运行正常，问题在于CSS。
        </p>
        
        <div style={{ marginTop: '20px' }}>
          <div style={{
            width: '20px',
            height: '20px',
            backgroundColor: '#3b82f6',
            display: 'inline-block',
            marginRight: '10px'
          }}></div>
          <span>蓝色方块（内联样式）</span>
        </div>
        
        <div style={{ marginTop: '10px' }}>
          <div style={{
            width: '20px',
            height: '20px',
            backgroundColor: '#10b981',
            display: 'inline-block',
            marginRight: '10px'
          }}></div>
          <span>绿色方块（内联样式）</span>
        </div>
      </div>
      
      <div style={{
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px'
      }}>
        <h2 style={{ color: '#666', fontSize: '18px', marginBottom: '10px' }}>
          图标测试（SVG）
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
          <span style={{ marginLeft: '8px' }}>小星星图标 (16px)</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12,6 12,12 16,14"/>
          </svg>
          <span style={{ marginLeft: '8px' }}>时钟图标 (24px)</span>
        </div>
      </div>
    </div>
  )
}