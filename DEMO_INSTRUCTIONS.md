# 🎯 BIG DATA E-COMMERCE ANALYTICS - QUICK DEMO GUIDE

## 🚀 **QUICK START (5 minutes)**

### **Step 1: Start the System**
```bash
# Double-click this file:
start_project.bat
```
**What happens:** All Big Data services start automatically:
- ✅ HDFS Distributed Storage 
- ✅ Spark Big Data Processing
- ✅ Machine Learning Pipeline
- ✅ Real-time Analytics Dashboard  
- ✅ E-commerce Web Application

### **Step 2: Open Demo URLs**
**The system will automatically open these URLs:**

| Service | URL | Purpose |
|---------|-----|---------|
| 🌐 **E-commerce App** | http://localhost:5000 | Interactive shopping site |
| 📊 **Analytics Dashboard** | http://localhost:8050 | **MAIN DEMO** - Big Data visualizations |
| 🗄️ **HDFS Storage** | http://localhost:9870 | Distributed file system |
| ⚡ **Spark Processing** | http://localhost:8080 | Big Data processing engine |

### **Step 3: Quick Demo (2 minutes)**
1. **Analytics Dashboard** (http://localhost:8050) → **Most Important!**
   - 📈 Real-time charts updating every 5 seconds
   - 👥 User segmentation from ML clustering
   - 🤖 Machine Learning performance metrics
   - 🛍️ Product analytics with big data

2. **E-commerce Site** (http://localhost:5000)
   - Login: `testuser` / `123456`
   - Click products → Creates real data
   - Check "Gợi ý cho bạn" → See ML recommendations

3. **Big Data Infrastructure**
   - **HDFS** (http://localhost:9870) → Distributed storage
   - **Spark** (http://localhost:8080) → Processing jobs

---

## 🏆 **REQUIREMENTS DEMONSTRATION**

### **✅ 1. Distributed Storage (2 điểm)**
**URL:** http://localhost:9870
**Demo:** 
- HDFS cluster with NameNode + 2 DataNodes
- Browse distributed file system
- See data replication across nodes
- **Evidence:** Multiple DataNodes visible, data partitioned

### **✅ 2. Big Data Processing (4 điểm)**  
**URL:** http://localhost:8080
**Demo:**
- Spark cluster with Master + 2 Workers
- MapReduce jobs processing user behavior
- Distributed computing across cluster
- **Evidence:** Running/Completed applications visible

### **✅ 3. Machine Learning (2 điểm)**
**Demo:** Automatic ML pipeline running
**Algorithms:**
- **K-Means Clustering:** User segmentation (5 clusters)
- **ALS Collaborative Filtering:** Product recommendations
- **Evidence:** Dashboard Tab 2 (User Segmentation) + Tab 4 (ML Metrics)

### **✅ 4. Data Visualization (2 điểm)**
**URL:** http://localhost:8050 ← **MAIN DEMO**
**Demo:**
- Real-time interactive dashboard with Plotly
- 4 tabs of visualizations:
  - 📈 Real-time Activity (hourly trends, categories)
  - 👥 User Segmentation (ML clustering results)  
  - 🛍️ Product Analytics (engagement, trends)
  - 🤖 Machine Learning (model performance)
- **Evidence:** Auto-updating charts every 5 seconds

---

## 🎯 **DEMO SCRIPT FOR PRESENTATION**

### **"Big Data E-commerce Analytics System"**

**"Chúng em xây dựng hệ thống phân tích Big Data cho thương mại điện tử với đầy đủ 4 yêu cầu:"**

#### **1. Lưu trữ phân tán (2 điểm)**
*[Show http://localhost:9870]*
- "HDFS cluster với 1 NameNode và 2 DataNode"
- "Dữ liệu được lưu phân tán và sao chép trên nhiều node"
- "Browse file system để xem cấu trúc phân tán"

#### **2. Xử lý dữ liệu lớn (4 điểm)**  
*[Show http://localhost:8080]*
- "Apache Spark cluster xử lý dữ liệu với MapReduce"
- "Spark SQL để phân tích hành vi người dùng"
- "Distributed computing trên multiple workers"

#### **3. Machine Learning (2 điểm)**
*[Show Dashboard Tab 2 & 4]*
- "K-Means clustering để phân đoạn người dùng thành 5 nhóm"
- "ALS Collaborative Filtering cho gợi ý sản phẩm"  
- "Metrics: RMSE, MAE, Coverage evaluation"

#### **4. Trực quan hóa (2 điểm)**
*[Show http://localhost:8050 - all tabs]*
- "Dashboard real-time với Plotly và interactive charts"
- "4 tabs: Activity, Segmentation, Products, ML Performance"
- "Auto-refresh mỗi 5 giây với dữ liệu mới"

**"Hệ thống đáp ứng đầy đủ yêu cầu Big Data và hoạt động real-time!"**

---

## 🛠️ **TROUBLESHOOTING**

### **If services don't start:**
```bash
# 1. Check Docker is running
docker --version

# 2. Restart Docker Desktop
# 3. Run setup manually:
scripts\setup_big_data.bat

# 4. Start project again:
start_project.bat
```

### **If ports are busy:**
- Check Task Manager for processes using ports 5000, 5002, 8050, 8080, 9870
- Close conflicting applications
- Restart the demo

### **If dashboard shows no data:**
- Go to http://localhost:5000
- Login and click some products
- Data will appear in dashboard within 5 seconds

---

## 📋 **DEMO CHECKLIST**

**Before Demo:**
- [ ] Docker Desktop running
- [ ] No conflicting applications on ports 5000, 5002, 8050, 8080, 9870
- [ ] Internet connection for Docker images download

**During Demo:**
- [ ] Show Analytics Dashboard first (most impressive)
- [ ] Demonstrate real-time updates  
- [ ] Show all 4 requirement components
- [ ] Generate some interaction data on e-commerce site
- [ ] Point out technical architecture (HDFS + Spark + ML)

**Key Talking Points:**
- ✅ "Distributed storage với HDFS cluster"
- ✅ "Big data processing với Apache Spark"  
- ✅ "Machine learning với clustering và collaborative filtering"
- ✅ "Real-time visualization với interactive dashboard"
- ✅ "Tự động refresh data mỗi 5 giây"

**🎯 Result: 10/10 điểm cho Big Data requirements!**