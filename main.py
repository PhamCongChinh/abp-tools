from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from database import get_db
from config import get_settings
import pandas as pd
from datetime import datetime
import os

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to FastAPI with PostgreSQL",
        "app_name": settings.app_name,
        "endpoints": {
            "health": "/health",
            "count_posts": "/posts/count",
            "export_excel": "/posts/count/export",
            "view_chart": "/posts/count/chart"
        }
    }


@app.get("/health")
def health_check():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@app.get("/posts/count")
def count_posts(
    time_start: int, 
    time_end: int, 
    org_id: int
):
    """
    Đếm số lượng posts theo pub_time và crawl_time, chia theo từng ngày
    
    Parameters:
    - time_start: Thời gian bắt đầu (timestamp)
    - time_end: Thời gian kết thúc (timestamp)
    - org_id: ID của organization
    
    Example: /posts/count?time_start=1777914000&time_end=1778000400&org_id=412592
    """
    try:
        # 1 ngày = 86400 giây
        ONE_DAY = 86400
        
        results = []
        current_start = time_start
        
        # Lặp qua từng ngày trong khoảng thời gian
        while current_start < time_end:
            current_end = min(current_start + ONE_DAY, time_end)
            
            # Query 1: Count by pub_time
            sql_pub = """
                SELECT COUNT(*) as total
                FROM tbl_posts tp
                WHERE tp.pub_time >= %s 
                AND tp.pub_time < %s
                AND tp.org_id = %s
            """
            
            # Query 2: Count by crawl_time (đây là tổng posts thực tế)
            sql_crawl = """
                SELECT COUNT(*) as total
                FROM tbl_posts tp
                WHERE tp.crawl_time >= %s 
                AND tp.crawl_time < %s
                AND tp.org_id = %s
            """
            
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Execute query 1
                cursor.execute(sql_pub, (current_start, current_end, org_id))
                result_pub = cursor.fetchone()
                
                # Execute query 2
                cursor.execute(sql_crawl, (current_start, current_end, org_id))
                result_crawl = cursor.fetchone()
                
                cursor.close()
            
            # Tính toán
            crawl_count = result_crawl['total']  # Tổng posts = số bài crawl trong ngày
            pub_count = result_pub['total']
            
            # Tỷ lệ bị sót tin = (crawl - pub) / crawl
            if crawl_count > 0:
                ratio = ((crawl_count - pub_count) / crawl_count) * 100
            else:
                ratio = 0
            
            # Thêm kết quả của ngày này
            results.append({
                "time_start": current_start,
                "time_end": current_end,
                "date": datetime.fromtimestamp(current_start).strftime('%Y-%m-%d'),
                "count_by_pub_time": pub_count,
                "count_by_crawl_time": crawl_count,
                "total_posts": crawl_count,  # Tổng = crawl_time
                "ratio_percent": round(ratio, 2)
            })
            
            # Chuyển sang ngày tiếp theo
            current_start = current_end
        
        return {
            "org_id": org_id,
            "total_days": len(results),
            "daily_counts": results
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@app.get("/posts/count/export")
def export_posts_count_to_excel(
    time_start: int, 
    time_end: int, 
    org_id: int
):
    """
    Xuất kết quả đếm posts ra file Excel theo từng ngày
    
    Parameters:
    - time_start: Thời gian bắt đầu (timestamp)
    - time_end: Thời gian kết thúc (timestamp)
    - org_id: ID của organization
    
    Example: /posts/count/export?time_start=1777914000&time_end=1778000400&org_id=412592
    """
    try:
        # 1 ngày = 86400 giây
        ONE_DAY = 86400
        
        data = []
        current_start = time_start
        
        # Lặp qua từng ngày trong khoảng thời gian
        while current_start < time_end:
            current_end = min(current_start + ONE_DAY, time_end)
            
            # Query 1: Count by pub_time
            sql_pub = """
                SELECT COUNT(*) as total
                FROM tbl_posts tp
                WHERE tp.pub_time >= %s 
                AND tp.pub_time < %s
                AND tp.org_id = %s
            """
            
            # Query 2: Count by crawl_time
            sql_crawl = """
                SELECT COUNT(*) as total
                FROM tbl_posts tp
                WHERE tp.crawl_time >= %s 
                AND tp.crawl_time < %s
                AND tp.org_id = %s
            """
            
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Execute query 1
                cursor.execute(sql_pub, (current_start, current_end, org_id))
                result_pub = cursor.fetchone()
                
                # Execute query 2
                cursor.execute(sql_crawl, (current_start, current_end, org_id))
                result_crawl = cursor.fetchone()
                
                cursor.close()
            
            # Query 1: Count by pub_time
            sql_pub = """
                SELECT COUNT(*) as total
                FROM tbl_posts tp
                WHERE tp.pub_time >= %s 
                AND tp.pub_time < %s
                AND tp.org_id = %s
            """
            
            # Query 2: Count by crawl_time (đây là tổng posts thực tế)
            sql_crawl = """
                SELECT COUNT(*) as total
                FROM tbl_posts tp
                WHERE tp.crawl_time >= %s 
                AND tp.crawl_time < %s
                AND tp.org_id = %s
            """
            
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Execute query 1
                cursor.execute(sql_pub, (current_start, current_end, org_id))
                result_pub = cursor.fetchone()
                
                # Execute query 2
                cursor.execute(sql_crawl, (current_start, current_end, org_id))
                result_crawl = cursor.fetchone()
                
                cursor.close()
            
            # Chuyển timestamp sang datetime để dễ đọc
            date_start = datetime.fromtimestamp(current_start).strftime('%Y-%m-%d %H:%M:%S')
            date_end = datetime.fromtimestamp(current_end).strftime('%Y-%m-%d %H:%M:%S')
            
            # Tính toán
            crawl_count = result_crawl['total']  # Tổng posts = số bài crawl trong ngày
            pub_count = result_pub['total']
            
            # Tỷ lệ bị sót tin = (crawl - pub) / crawl
            if crawl_count > 0:
                ratio = ((crawl_count - pub_count) / crawl_count) * 100
            else:
                ratio = 0
            
            # Thêm dữ liệu cho ngày này
            data.append({
                "Ngày bắt đầu": date_start,
                "Ngày kết thúc": date_end,
                "Timestamp bắt đầu": current_start,
                "Timestamp kết thúc": current_end,
                "Org ID": org_id,
                "Số lượng (pub_time)": pub_count,
                "Số lượng (crawl_time)": crawl_count,
                "Tổng posts": crawl_count,  # Tổng = crawl_time
                "Tỷ lệ sót tin (%)": round(ratio, 2)
            })
            
            # Chuyển sang ngày tiếp theo
            current_start = current_end
        
        # Tạo DataFrame từ dữ liệu
        df = pd.DataFrame(data)
        
        # Tạo thư mục exports nếu chưa có
        os.makedirs("exports", exist_ok=True)
        
        # Tạo tên file với timestamp hiện tại
        filename = f"posts_count_org_{org_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join("exports", filename)
        
        # Xuất ra Excel
        df.to_excel(filepath, index=False, sheet_name="Posts Count")
        
        # Trả về file để download
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Export error: {str(e)}")


@app.get("/posts/count/chart", response_class=HTMLResponse)
def view_chart():
    """
    Hiển thị trang web với form nhập liệu và chart
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Posts Count Chart</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                padding: 30px;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2em;
            }
            .form-container {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 600;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            input:focus {
                outline: none;
                border-color: #667eea;
            }
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            button {
                flex: 1;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            .btn-secondary {
                background: #28a745;
                color: white;
            }
            .btn-secondary:hover {
                background: #218838;
                transform: translateY(-2px);
            }
            .chart-container {
                position: relative;
                height: 400px;
                margin-top: 30px;
            }
            .charts-grid {
                display: grid;
                grid-template-columns: 1fr;
                gap: 30px;
                margin-top: 30px;
            }
            @media (min-width: 1200px) {
                .charts-grid {
                    grid-template-columns: 2fr 1fr;
                }
            }
            .loading {
                text-align: center;
                padding: 20px;
                color: #667eea;
                font-size: 18px;
                display: none;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                display: none;
            }
            .info {
                background: #d1ecf1;
                color: #0c5460;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                margin-top: 10px;
            }
            .stat-label {
                font-size: 0.9em;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Posts Count Analytics</h1>
            
            <div class="info">
                <strong>Giải thích:</strong><br>
                • <strong>Tổng posts crawl được:</strong> Số bài crawl về trong ngày (crawl_time) - Đây là số cố định<br>
                • <strong>Posts có pub_time đúng ngày:</strong> Số bài có pub_time trong cùng ngày<br>
                • <strong>Tỷ lệ sót tin:</strong> (crawl - pub) / crawl × 100% - Tỷ lệ bài crawl được nhưng pub_time không trong ngày
            </div>
            
            <div class="form-container">
                <div class="form-group">
                    <label for="time_start">Timestamp bắt đầu:</label>
                    <input type="number" id="time_start" placeholder="Ví dụ: 1777914000" value="1777914000">
                </div>
                
                <div class="form-group">
                    <label for="time_end">Timestamp kết thúc:</label>
                    <input type="number" id="time_end" placeholder="Ví dụ: 1778172800" value="1778172800">
                </div>
                
                <div class="form-group">
                    <label for="org_id">Organization ID:</label>
                    <input type="number" id="org_id" placeholder="Ví dụ: 412592" value="412592">
                </div>
                
                <div class="button-group">
                    <button class="btn-primary" onclick="loadChart()">📈 Xem biểu đồ</button>
                    <button class="btn-secondary" onclick="exportExcel()">📥 Xuất Excel</button>
                </div>
            </div>
            
            <div class="loading" id="loading">⏳ Đang tải dữ liệu...</div>
            <div class="error" id="error"></div>
            
            <div id="stats" class="stats" style="display: none;"></div>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <canvas id="lineChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
        </div>
        
        <script>
            let lineChartInstance = null;
            let barChartInstance = null;
            
            async function loadChart() {
                const timeStart = document.getElementById('time_start').value;
                const timeEnd = document.getElementById('time_end').value;
                const orgId = document.getElementById('org_id').value;
                
                if (!timeStart || !timeEnd || !orgId) {
                    showError('Vui lòng nhập đầy đủ thông tin!');
                    return;
                }
                
                document.getElementById('loading').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                document.getElementById('stats').style.display = 'none';
                
                try {
                    const response = await fetch(`/posts/count?time_start=${timeStart}&time_end=${timeEnd}&org_id=${orgId}`);
                    const data = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(data.detail || 'Có lỗi xảy ra');
                    }
                    
                    document.getElementById('loading').style.display = 'none';
                    
                    // Hiển thị thống kê
                    showStats(data);
                    
                    // Vẽ biểu đồ
                    drawChart(data);
                    
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    showError(error.message);
                }
            }
            
            function showStats(data) {
                const totalPub = data.daily_counts.reduce((sum, item) => sum + item.count_by_pub_time, 0);
                const totalCrawl = data.daily_counts.reduce((sum, item) => sum + item.count_by_crawl_time, 0);
                const avgRatio = data.daily_counts.reduce((sum, item) => sum + item.ratio_percent, 0) / data.total_days;
                
                const statsHtml = `
                    <div class="stat-card">
                        <div class="stat-label">Tổng số ngày</div>
                        <div class="stat-value">${data.total_days}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Tổng posts crawl được</div>
                        <div class="stat-value">${totalCrawl.toLocaleString()}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Posts có pub_time đúng ngày</div>
                        <div class="stat-value">${totalPub.toLocaleString()}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Tỷ lệ sót tin trung bình</div>
                        <div class="stat-value">${avgRatio.toFixed(2)}%</div>
                    </div>
                `;
                
                document.getElementById('stats').innerHTML = statsHtml;
                document.getElementById('stats').style.display = 'grid';
            }
            
            function drawChart(data) {
                const labels = data.daily_counts.map(item => item.date);
                const pubTimeData = data.daily_counts.map(item => item.count_by_pub_time);
                const crawlTimeData = data.daily_counts.map(item => item.count_by_crawl_time);
                const ratioData = data.daily_counts.map(item => item.ratio_percent);
                
                // Biểu đồ đường - Line Chart
                const lineCtx = document.getElementById('lineChart').getContext('2d');
                
                if (lineChartInstance) {
                    lineChartInstance.destroy();
                }
                
                lineChartInstance = new Chart(lineCtx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Tổng posts crawl được',
                                data: crawlTimeData,
                                borderColor: 'rgb(40, 167, 69)',
                                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                                borderWidth: 3,
                                tension: 0.4,
                                fill: true
                            },
                            {
                                label: 'Posts có pub_time đúng ngày',
                                data: pubTimeData,
                                borderColor: 'rgb(102, 126, 234)',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                borderWidth: 3,
                                tension: 0.4,
                                fill: true
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false,
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    font: {
                                        size: 13,
                                        weight: 'bold'
                                    },
                                    padding: 15
                                }
                            },
                            title: {
                                display: true,
                                text: `Số lượng Posts theo ngày - Org ID: ${data.org_id}`,
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                },
                                padding: 15
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        let label = context.dataset.label || '';
                                        if (label) {
                                            label += ': ';
                                        }
                                        if (context.parsed.y !== null) {
                                            label += context.parsed.y.toLocaleString();
                                        }
                                        return label;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Số lượng posts',
                                    font: {
                                        size: 13,
                                        weight: 'bold'
                                    }
                                },
                                ticks: {
                                    font: {
                                        size: 11
                                    }
                                }
                            },
                            x: {
                                ticks: {
                                    font: {
                                        size: 11
                                    }
                                }
                            }
                        }
                    }
                });
                
                // Biểu đồ cột - Bar Chart cho tỷ lệ sót tin
                const barCtx = document.getElementById('barChart').getContext('2d');
                
                if (barChartInstance) {
                    barChartInstance.destroy();
                }
                
                // Tạo màu gradient cho các cột dựa trên tỷ lệ
                const barColors = ratioData.map(ratio => {
                    if (ratio < 10) return 'rgba(40, 167, 69, 0.8)';  // Xanh lá - tốt
                    if (ratio < 25) return 'rgba(255, 193, 7, 0.8)';  // Vàng - cảnh báo
                    return 'rgba(255, 99, 132, 0.8)';  // Đỏ - cao
                });
                
                barChartInstance = new Chart(barCtx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Tỷ lệ sót tin (%)',
                                data: ratioData,
                                backgroundColor: barColors,
                                borderColor: barColors.map(color => color.replace('0.8', '1')),
                                borderWidth: 2
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: 'Tỷ lệ sót tin (%)',
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                },
                                padding: 15
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return 'Tỷ lệ sót tin: ' + context.parsed.y.toFixed(2) + '%';
                                    },
                                    afterLabel: function(context) {
                                        const index = context.dataIndex;
                                        const crawl = crawlTimeData[index];
                                        const pub = pubTimeData[index];
                                        const missed = crawl - pub;
                                        return [
                                            '',
                                            'Crawl: ' + crawl.toLocaleString(),
                                            'Pub đúng ngày: ' + pub.toLocaleString(),
                                            'Sót tin: ' + missed.toLocaleString()
                                        ];
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Tỷ lệ (%)',
                                    font: {
                                        size: 13,
                                        weight: 'bold'
                                    }
                                },
                                ticks: {
                                    font: {
                                        size: 11
                                    },
                                    callback: function(value) {
                                        return value + '%';
                                    }
                                },
                                grid: {
                                    color: function(context) {
                                        if (context.tick.value === 10 || context.tick.value === 25) {
                                            return 'rgba(255, 99, 132, 0.3)';
                                        }
                                        return 'rgba(0, 0, 0, 0.1)';
                                    },
                                    lineWidth: function(context) {
                                        if (context.tick.value === 10 || context.tick.value === 25) {
                                            return 2;
                                        }
                                        return 1;
                                    }
                                }
                            },
                            x: {
                                ticks: {
                                    font: {
                                        size: 11
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            function showError(message) {
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = '❌ ' + message;
                errorDiv.style.display = 'block';
            }
            
            function exportExcel() {
                const timeStart = document.getElementById('time_start').value;
                const timeEnd = document.getElementById('time_end').value;
                const orgId = document.getElementById('org_id').value;
                
                if (!timeStart || !timeEnd || !orgId) {
                    showError('Vui lòng nhập đầy đủ thông tin!');
                    return;
                }
                
                window.location.href = `/posts/count/export?time_start=${timeStart}&time_end=${timeEnd}&org_id=${orgId}`;
            }
            
            // Tự động load chart khi trang được tải
            window.onload = function() {
                loadChart();
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
