from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from database import get_db
from config import get_settings
from typing import Optional
import pandas as pd
from datetime import datetime
import os

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)

VALID_SOURCES = {"fb", "tt", "yt", "web"}


def build_queries(crawl_source_code: Optional[str]) -> tuple[str, str, list]:
    """
    - sql_crawl       : tổng bài crawl về trong ngày (theo crawl_time)
    - sql_missed      : bài crawl về hôm nay nhưng pub_time < crawl_time - 12h (sót tin)
    """
    source_clause = ""
    source_params = []
    if crawl_source_code:
        source_clause = "AND tp.crawl_source_code = %s"
        source_params = [crawl_source_code]

    # Query 1: tổng bài crawl về trong ngày
    sql_crawl = f"""
        SELECT COUNT(*) as total
        FROM tbl_posts tp
        WHERE tp.crawl_time >= %s
        AND tp.crawl_time < %s
        AND tp.org_id = %s
        {source_clause}
    """

    # Query 2: bài crawl về hôm nay nhưng pub_time < crawl_time - 12 giờ (43200 giây)
    # → bài đã đăng hơn 12 tiếng trước mới crawl được = sót tin
    sql_missed = f"""
        SELECT COUNT(*) as total
        FROM tbl_posts tp
        WHERE tp.crawl_time >= %s
        AND tp.crawl_time < %s
        AND tp.pub_time < (tp.crawl_time - 43200)
        AND tp.org_id = %s
        {source_clause}
    """

    return sql_crawl, sql_missed, source_params


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
            cursor.fetchone()
            cursor.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@app.get("/posts/count")
def count_posts(
    time_start: int,
    time_end: int,
    org_id: int,
    crawl_source_code: Optional[str] = None
):
    """
    Đếm số lượng posts theo pub_time và crawl_time, chia theo từng ngày.

    Parameters:
    - time_start: Thời gian bắt đầu (timestamp)
    - time_end: Thời gian kết thúc (timestamp)
    - org_id: ID của organization
    - crawl_source_code: (tuỳ chọn) Lọc theo nguồn: fb | tt | yt | web. Bỏ trống = tất cả nguồn.

    Example: /posts/count?time_start=1777914000&time_end=1778000400&org_id=412592&crawl_source_code=fb
    """
    if crawl_source_code and crawl_source_code not in VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail=f"crawl_source_code không hợp lệ. Chỉ chấp nhận: {', '.join(sorted(VALID_SOURCES))}"
        )

    try:
        ONE_DAY = 86400
        results = []
        current_start = time_start

        sql_crawl, sql_missed, source_params = build_queries(crawl_source_code)

        while current_start < time_end:
            current_end = min(current_start + ONE_DAY, time_end)

            with get_db() as conn:
                cursor = conn.cursor()

                # Tổng bài crawl về trong ngày
                cursor.execute(sql_crawl, [current_start, current_end, org_id] + source_params)
                result_crawl = cursor.fetchone()

                # Bài sót tin: crawl hôm nay nhưng pub_time < crawl_time - 12h
                cursor.execute(sql_missed, [current_start, current_end, org_id] + source_params)
                result_missed = cursor.fetchone()

                cursor.close()

            crawl_count  = result_crawl['total']
            missed_count = result_missed['total']
            on_time      = crawl_count - missed_count

            ratio = (missed_count / crawl_count * 100) if crawl_count > 0 else 0

            results.append({
                "time_start": current_start,
                "time_end": current_end,
                "date": datetime.fromtimestamp(current_start).strftime('%Y-%m-%d'),
                "count_by_crawl_time": crawl_count,
                "count_pub_same_day": on_time,
                "count_missed": missed_count,
                "ratio_percent": round(ratio, 2)
            })

            current_start = current_end

        return {
            "org_id": org_id,
            "crawl_source_code": crawl_source_code or "all",
            "total_days": len(results),
            "daily_counts": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@app.get("/posts/count/export")
def export_posts_count_to_excel(
    time_start: int,
    time_end: int,
    org_id: int,
    crawl_source_code: Optional[str] = None
):
    """
    Xuất kết quả đếm posts ra file Excel theo từng ngày.

    Parameters:
    - time_start: Thời gian bắt đầu (timestamp)
    - time_end: Thời gian kết thúc (timestamp)
    - org_id: ID của organization
    - crawl_source_code: (tuỳ chọn) Lọc theo nguồn: fb | tt | yt | web. Bỏ trống = tất cả nguồn.

    Example: /posts/count/export?time_start=1777914000&time_end=1778000400&org_id=412592&crawl_source_code=fb
    """
    if crawl_source_code and crawl_source_code not in VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail=f"crawl_source_code không hợp lệ. Chỉ chấp nhận: {', '.join(sorted(VALID_SOURCES))}"
        )

    try:
        ONE_DAY = 86400
        data = []
        current_start = time_start

        sql_crawl, sql_missed, source_params = build_queries(crawl_source_code)

        while current_start < time_end:
            current_end = min(current_start + ONE_DAY, time_end)

            with get_db() as conn:
                cursor = conn.cursor()

                cursor.execute(sql_crawl, [current_start, current_end, org_id] + source_params)
                result_crawl = cursor.fetchone()

                cursor.execute(sql_missed, [current_start, current_end, org_id] + source_params)
                result_missed = cursor.fetchone()

                cursor.close()

            date_start   = datetime.fromtimestamp(current_start).strftime('%Y-%m-%d %H:%M:%S')
            date_end     = datetime.fromtimestamp(current_end).strftime('%Y-%m-%d %H:%M:%S')

            crawl_count  = result_crawl['total']
            missed_count = result_missed['total']
            on_time      = crawl_count - missed_count
            ratio        = (missed_count / crawl_count * 100) if crawl_count > 0 else 0

            data.append({
                "Ngày bắt đầu": date_start,
                "Ngày kết thúc": date_end,
                "Timestamp bắt đầu": current_start,
                "Timestamp kết thúc": current_end,
                "Org ID": org_id,
                "Nguồn (crawl_source_code)": crawl_source_code or "all",
                "Tổng bài crawl về (crawl_time)": crawl_count,
                "Bài crawl đúng hạn (pub < 12h)": on_time,
                "Bài sót tin (pub_time > crawl_time - 12h)": missed_count,
                "Tỷ lệ sót tin (%)": round(ratio, 2)
            })

            current_start = current_end

        df = pd.DataFrame(data)

        os.makedirs("exports", exist_ok=True)

        source_suffix = f"_{crawl_source_code}" if crawl_source_code else "_all"
        filename = f"posts_count_org_{org_id}{source_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join("exports", filename)

        df.to_excel(filepath, index=False, sheet_name="Posts Count")

        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise
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
            * { margin: 0; padding: 0; box-sizing: border-box; }
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
            h1 { color: #333; text-align: center; margin-bottom: 30px; font-size: 2em; }
            .form-container {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 30px;
            }
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            @media (max-width: 768px) { .form-row { grid-template-columns: 1fr; } }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #555; font-weight: 600; }
            input, select {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
                background: white;
            }
            input:focus, select:focus { outline: none; border-color: #667eea; }
            .source-badges {
                display: flex;
                gap: 8px;
                margin-top: 8px;
                flex-wrap: wrap;
            }
            .badge {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                border: 2px solid transparent;
                transition: all 0.2s;
            }
            .badge-all  { background: #e9ecef; color: #495057; }
            .badge-fb   { background: #e7f0fd; color: #1877f2; border-color: #1877f2; }
            .badge-tt   { background: #ffe8ec; color: #fe2c55; border-color: #fe2c55; }
            .badge-yt   { background: #fff0f0; color: #ff0000; border-color: #ff0000; }
            .badge-web  { background: #e8f5e9; color: #2e7d32; border-color: #2e7d32; }
            .badge:hover { opacity: 0.75; }
            .button-group { display: flex; gap: 10px; margin-top: 20px; }
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
            .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102,126,234,0.4); }
            .btn-secondary { background: #28a745; color: white; }
            .btn-secondary:hover { background: #218838; transform: translateY(-2px); }
            .chart-container { position: relative; height: 400px; margin-top: 30px; }
            .charts-grid { display: grid; grid-template-columns: 1fr; gap: 30px; margin-top: 30px; }
            @media (min-width: 1200px) { .charts-grid { grid-template-columns: 2fr 1fr; } }
            .loading { text-align: center; padding: 20px; color: #667eea; font-size: 18px; display: none; }
            .error {
                background: #f8d7da; color: #721c24;
                padding: 15px; border-radius: 8px; margin-top: 20px; display: none;
            }
            .info {
                background: #d1ecf1; color: #0c5460;
                padding: 15px; border-radius: 8px; margin-bottom: 20px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px; margin-top: 20px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 20px; border-radius: 10px; text-align: center;
            }
            .stat-value { font-size: 2em; font-weight: bold; margin-top: 10px; }
            .stat-label { font-size: 0.9em; opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Posts Count Analytics</h1>

            <div class="info">
                <strong>Giải thích cách tính:</strong><br>
                • <strong>Tổng bài crawl về:</strong> Số bài có <code>crawl_time</code> trong ngày đó<br>
                • <strong>Bài crawl đúng hạn:</strong> Bài crawl về hôm nay mà <code>pub_time ≥ crawl_time - 12h</code> (bài mới, không sót)<br>
                • <strong>Bài sót tin:</strong> Bài crawl về hôm nay nhưng <code>pub_time &lt; crawl_time - 12h</code> (bài đã đăng hơn 12 tiếng mới crawl được)<br>
                • <strong>Tỷ lệ sót tin:</strong> Sót tin / Tổng crawl × 100%<br>
                • <strong>Nguồn:</strong> Bỏ trống = tất cả nguồn. Chọn fb / tt / yt / web để lọc theo nguồn cụ thể.
            </div>

            <div class="form-container">
                <div class="form-row">
                    <div class="form-group">
                        <label for="time_start">Timestamp bắt đầu:</label>
                        <input type="number" id="time_start" placeholder="Ví dụ: 1777914000" value="1777914000">
                    </div>
                    <div class="form-group">
                        <label for="time_end">Timestamp kết thúc:</label>
                        <input type="number" id="time_end" placeholder="Ví dụ: 1778172800" value="1778172800">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="org_id">Organization ID:</label>
                        <input type="number" id="org_id" placeholder="Ví dụ: 412592" value="412592">
                    </div>
                    <div class="form-group">
                        <label for="crawl_source_code">Nguồn (crawl_source_code):</label>
                        <select id="crawl_source_code">
                            <option value="">-- Tất cả nguồn --</option>
                            <option value="fb">fb — Facebook</option>
                            <option value="tt">tt — TikTok</option>
                            <option value="yt">yt — YouTube</option>
                            <option value="web">web — Website</option>
                        </select>
                        <div class="source-badges">
                            <span class="badge badge-all" onclick="setSource('')">Tất cả</span>
                            <span class="badge badge-fb"  onclick="setSource('fb')">📘 fb</span>
                            <span class="badge badge-tt"  onclick="setSource('tt')">🎵 tt</span>
                            <span class="badge badge-yt"  onclick="setSource('yt')">▶️ yt</span>
                            <span class="badge badge-web" onclick="setSource('web')">🌐 web</span>
                        </div>
                    </div>
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

            function setSource(value) {
                document.getElementById('crawl_source_code').value = value;
            }

            function buildParams() {
                const timeStart = document.getElementById('time_start').value;
                const timeEnd   = document.getElementById('time_end').value;
                const orgId     = document.getElementById('org_id').value;
                const source    = document.getElementById('crawl_source_code').value;

                if (!timeStart || !timeEnd || !orgId) {
                    showError('Vui lòng nhập đầy đủ thông tin!');
                    return null;
                }

                let params = `time_start=${timeStart}&time_end=${timeEnd}&org_id=${orgId}`;
                if (source) params += `&crawl_source_code=${source}`;
                return params;
            }

            async function loadChart() {
                const params = buildParams();
                if (!params) return;

                document.getElementById('loading').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                document.getElementById('stats').style.display = 'none';

                try {
                    const response = await fetch(`/posts/count?${params}`);
                    const data = await response.json();

                    if (!response.ok) throw new Error(data.detail || 'Có lỗi xảy ra');

                    document.getElementById('loading').style.display = 'none';
                    showStats(data);
                    drawChart(data);
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    showError(error.message);
                }
            }

            function showStats(data) {
                const totalCrawl    = data.daily_counts.reduce((s, i) => s + i.count_by_crawl_time, 0);
                const totalPubSame  = data.daily_counts.reduce((s, i) => s + i.count_pub_same_day, 0);
                const totalMissed   = data.daily_counts.reduce((s, i) => s + i.count_missed, 0);
                const avgRatio      = data.daily_counts.reduce((s, i) => s + i.ratio_percent, 0) / data.total_days;
                const sourceLabel   = data.crawl_source_code === 'all' ? 'Tất cả nguồn' : data.crawl_source_code.toUpperCase();

                document.getElementById('stats').innerHTML = `
                    <div class="stat-card">
                        <div class="stat-label">Nguồn dữ liệu</div>
                        <div class="stat-value" style="font-size:1.4em">${sourceLabel}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Tổng số ngày</div>
                        <div class="stat-value">${data.total_days}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Tổng bài crawl về</div>
                        <div class="stat-value">${totalCrawl.toLocaleString()}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Bài crawl đúng hạn</div>
                        <div class="stat-value">${totalPubSame.toLocaleString()}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Bài sót tin (pub > 12h)</div>
                        <div class="stat-value">${totalMissed.toLocaleString()}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Tỷ lệ sót tin trung bình</div>
                        <div class="stat-value">${avgRatio.toFixed(2)}%</div>
                    </div>
                `;
                document.getElementById('stats').style.display = 'grid';
            }

            function drawChart(data) {
                const labels        = data.daily_counts.map(i => i.date);
                const crawlData     = data.daily_counts.map(i => i.count_by_crawl_time);
                const pubSameData   = data.daily_counts.map(i => i.count_pub_same_day);
                const missedData    = data.daily_counts.map(i => i.count_missed);
                const ratioData     = data.daily_counts.map(i => i.ratio_percent);
                const sourceLabel   = data.crawl_source_code === 'all' ? 'Tất cả nguồn' : data.crawl_source_code.toUpperCase();

                // --- Line Chart ---
                if (lineChartInstance) lineChartInstance.destroy();
                lineChartInstance = new Chart(
                    document.getElementById('lineChart').getContext('2d'), {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [
                            {
                                label: 'Tổng bài crawl về',
                                data: crawlData,
                                borderColor: 'rgb(40, 167, 69)',
                                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                                borderWidth: 3, tension: 0.4, fill: true
                            },
                            {
                                label: 'Bài crawl đúng hạn (pub < 12h)',
                                data: pubSameData,
                                borderColor: 'rgb(102, 126, 234)',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                borderWidth: 3, tension: 0.4, fill: true
                            },
                            {
                                label: 'Bài sót tin (pub > 12h)',
                                data: missedData,
                                borderColor: 'rgb(255, 99, 132)',
                                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                                borderWidth: 2, tension: 0.4, fill: true,
                                borderDash: [5, 5]
                            }
                        ]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        plugins: {
                            legend: { position: 'top', labels: { font: { size: 13, weight: 'bold' }, padding: 15 } },
                            title: {
                                display: true,
                                text: `Số lượng Posts theo ngày — Org ${data.org_id} | Nguồn: ${sourceLabel}`,
                                font: { size: 15, weight: 'bold' }, padding: 15
                            },
                            tooltip: {
                                callbacks: {
                                    label: ctx => (ctx.dataset.label || '') + ': ' + ctx.parsed.y.toLocaleString()
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Số lượng bài', font: { size: 13, weight: 'bold' } }
                            }
                        }
                    }
                });

                // --- Bar Chart ---
                if (barChartInstance) barChartInstance.destroy();
                const barColors = ratioData.map(r =>
                    r < 10  ? 'rgba(40, 167, 69, 0.8)' :
                    r < 25  ? 'rgba(255, 193, 7, 0.8)' :
                              'rgba(255, 99, 132, 0.8)'
                );
                barChartInstance = new Chart(
                    document.getElementById('barChart').getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [{
                            label: 'Tỷ lệ sót tin (%)',
                            data: ratioData,
                            backgroundColor: barColors,
                            borderColor: barColors.map(c => c.replace('0.8', '1')),
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            title: {
                                display: true,
                                text: `Tỷ lệ sót tin (%) | Nguồn: ${sourceLabel}`,
                                font: { size: 15, weight: 'bold' }, padding: 15
                            },
                            tooltip: {
                                callbacks: {
                                    label: ctx => 'Tỷ lệ sót tin: ' + ctx.parsed.y.toFixed(2) + '%',
                                    afterLabel: ctx => {
                                        const i = ctx.dataIndex;
                                        return [
                                            '',
                                            'Tổng crawl: '           + crawlData[i].toLocaleString(),
                                            'Pub đúng ngày: '        + pubSameData[i].toLocaleString(),
                                            'Sót tin: '              + missedData[i].toLocaleString()
                                        ];
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Tỷ lệ (%)', font: { size: 13, weight: 'bold' } },
                                ticks: { callback: v => v + '%' },
                                grid: {
                                    color: 'rgba(0,0,0,0.1)',
                                    lineWidth: 1
                                }
                            }
                        }
                    }
                });
            }

            function showError(message) {
                const el = document.getElementById('error');
                el.textContent = '❌ ' + message;
                el.style.display = 'block';
            }

            function exportExcel() {
                const params = buildParams();
                if (!params) return;
                window.location.href = `/posts/count/export?${params}`;
            }

            window.onload = loadChart;
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
