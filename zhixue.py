# 作者: 7912, Pomelo
import requests, json, time



# 账号列表.
accountList = {
    "学校名称": {
        "account": 9876543210123456789, # 教师账号. (19位数字)
        "password": "password", # 密码.
        "session": requests.Session(),
        "data": {}
    },
}


# 登录 accountList 中的账号, 并将会话信息存至其字典的 session 中. 
def login(account, showProgress = False):
    if account not in accountList: # 检查账号是否在 accountList 中.
        raise Exception("账号未找到.")
    username, password, session = accountList[account]["account"], accountList[account]["password"], accountList[account]["session"] # 取出账号, 密码以及会话信息.

    # 登录第一部分, 发送登录请求.
    if showProgress: print("[0/3] 发送登录请求.")
    data = {
        "service": "https://www.zhixue.com:443/ssoservice.jsp",
    }
    result = session.get("https://sso.zhixue.com/sso_alpha/login", params = data).text
    result = json.loads(result.split("('", 1)[1].split("')")[0].replace("\\", ""))
    if result["result"] != "success": # 检查是否成功请求.
        raise Exception(result["data"])
    if "st" in result["data"]: # 检查此会话是否已经登录了.
        return # 如果 st 在返回值中, 说明此会话已经在登录状态了, 所以停止执行.
    lt = result["data"]["lt"] # 获取临时凭证1.
    execution = result["data"]["execution"] # 获取临时凭证2.

    # 登录第二部分, 发送账号, 密码以及第一部分中获取到的临时凭证.
    if showProgress: print("[1/3] 发送账号密码.")
    data = {
        "username": username,
        "password": password,
        "key": "id",
        "_eventId": "submit",
        "lt": lt,
        "execution": execution,
    }
    result = session.get("https://sso.zhixue.com/sso_alpha/login", params = data).text
    result = json.loads(result.split("('", 1)[1].split("')")[0].replace("\\", ""))
    if result["result"] != "success": # 检查登录凭证是否成功获取.
        raise Exception(result["data"])
    if "st" not in result["data"]: # 检查登录凭证是否成功获取.
        raise Exception("st 未找到.")
    st = result["data"]["st"]

    # 登录第三部分, 发送登录凭证, 完成登录.
    if showProgress: print("[2/3] 检查登录状态.")
    data = {
        "ticket": st,
    }
    result = session.post("https://www.zhixue.com/ssoservice.jsp", params = data).text
    result = result.split("\n", 1)[0]
    if result != "success": # 检查登录是否成功.
        raise Exception(result)
    if showProgress: print("[3/3] 登录成功.")


# 通过对应账号的会话进行 requests.get, 获取信息.
def getData(account, url):
    if account not in accountList:
        raise Exception("学校未找到.")
    result = accountList[account]["session"].get(url).text # 通过会话获取数据.
    if result.startswith("<!DOCTYPE html>"): # 检查是否获取到数据了.
        login(account) # 如果智学网返回的是 html 代码, 说明没有登录或会话过期或数据不存在, 所以重新尝试登录.
        result = accountList[account]["session"].get(url).text # 再次获取数据.
        if result.startswith("<!DOCTYPE html>"): # 如果智学网返回的还是 html 代码, 说明排除了没有登录或会话过期的可能, 只有可能是数据不存在.
            raise Exception("获取失败.")
    result = json.loads(result)
    if result["message"]: # 如果智学网返回信息中 message 的值不是空的, 说明获取出错, 同时 message 的值就是错误详情.
        if result["message"] == "内部错误": # 如果错误是 内部错误, 其实就是数据没找到.
            result["message"] = "未查询到结果."
        raise Exception(result["message"])
    return result


# 根据级数 (入学年份) 获取考试列表.
def getExamListByYear(account, year, page = 1):
    result = getData(account, "https://www.zhixue.com/api-teacher/api/reportlist?queryType=schoolInYear&schoolInYearCode=%d&pageIndex=%d" % (year, page))
    return result


# 根据级数 (入学年份) 获取考试列表, 并将部分结果直接转换成文字.
def getExamListStrByYear(account, year, page = 1, limit = None):
    result = getExamListByYear(account, year, page)["result"]["reportList"]
    if not result:
        raise Exception("未查询到结果.")
    if limit:
        result = result[0:limit]
    string = ""
    for index, exam in enumerate(result):
        examUpdateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exam["data"]["createDateTime"]/1000))
        examName = exam["data"]["examName"] #hi 应该正常了
        examID = exam["data"]["examId"] # 这边是从智学网获取数据的, QQ机器人的代码在main.py里 
        isPublic = exam["isPublic"] # 现在科目状态有些bug, 不能完全获取到. 比如有物理, 化学, 但不能分别获取
        if not isPublic:
            string += ("%d. %s\n更新时间: %s,\nexamID: 无法获取\n\n" % (index+1, examName, examUpdateTime))
        else:
            string += ("%d. %s\n更新时间: %s,\nexamID: %s\n\n" % (index+1, examName, examUpdateTime, examID))
    return string[:-2]


# 根据年级 获取考试列表.
gradeName2gradeCode = {
    "初一": "07",
    "初二": "08",
    "初三": "09",
    "高一": "10",
    "高二": "11",
    "高三": "12",

}
def getExamListByGrade(account, grade, page = 1):
    if grade not in gradeName2gradeCode:
        raise ValueError("年级只能是 初/高 一/二/三.")
    result = getData(account, "https://www.zhixue.com/api-teacher/api/reportlist?beginTime=1&endTime=9999999999999&gradeCode=%s&pageIndex=%d" % (gradeName2gradeCode[grade], page))
    return result


# 根据年级 获取考试列表, 并将部分结果直接转换成文字.
def getExamListStrByGrade(account, grade, page = 1, limit = None):
    result = getExamListByGrade(account, grade, page)["result"]["reportList"]
    if not result:
        raise Exception("未查询到结果.")
    if limit:
        result = result[0:limit]
    string = ""
    for index, exam in enumerate(result):
        examUpdateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exam["data"]["createDateTime"]/1000))
        examName = exam["data"]["examName"] #hi 应该正常了
        examID = exam["data"]["examId"] # 这边是从智学网获取数据的, QQ机器人的代码在main.py里 
        isPublic = exam["isPublic"] # 现在科目状态有些bug, 不能完全获取到. 比如有物理, 化学, 但不能分别获取
        if not isPublic:
            string += ("%d. %s\n更新时间: %s,\nexamID: 学校未发布成绩, 无法获取\n\n" % (index+1, examName, examUpdateTime))
        else:
            string += ("%d. %s\n更新时间: %s,\nexamID: %s\n\n" % (index+1, examName, examUpdateTime, examID))
    return string[:-2]


# 获取考试列表.
def getExamListAll(account, page = 1):
    result = getData(account, "https://www.zhixue.com/api-teacher/api/reportlist?beginTime=1&endTime=9999999999999&pageIndex=%d" % page)
    return result


# 根据 examID 获取一场考试的详情.
def getExamDataByID(account, examID):
    result = getData(account, "https://www.zhixue.com/api-teacher/api/studentScore/studentExamScore?examId=%s" % examID)
    result["result"]["allSubjectTopicSetList"] = getData(account, "https://www.zhixue.com/api-teacher/api/examAnalysis/subjectList?examId=%s" % examID)["result"]["subjectList"]
    return result


# 根据 examID 获取一场考试的详情, 并将部分结果直接转换成文字.
def getExamDataStrByID(account, examID):
    examData = getExamDataByID(account, examID)["result"]
    string = ""
    isFinal = examData["isFinal"]
    examName = examData["examInfo"]["examName"]
    gradeName = examData["examInfo"]["gradeName"]
    schoolName = examData["examInfo"]["schoolName"]
    updateTime = examData["schoolExamArchive"]["createDateTime"]
    updateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updateTime/1000))
    studentTakedNum = examData["schoolExamArchive"]["submitStudentCount"]
    examType = examData["examType"]
    # avgScore = examData["schoolExamArchive"]["avgScore"]
    # maxScore = examData["schoolExamArchive"]["maxScore"]
    classList = examData["classList"]
    classList = [class_["name"] for class_ in classList]
    subjectList = examData["allSubjectTopicSetList"]
    subjectList = [subject["subjectName"] for subject in subjectList]
    string += ("学校名称: %s\n" % schoolName)
    string += ("考试名称: %s\n" % examName)
    string += ("考试年级: %s\n" % gradeName)
    string += ("考试类型: %s\n" % examType)
    string += ("更新时间: %s\n" % updateTime)
    string += ("参考人数: %s\n" % studentTakedNum)
    string += "状态: 已完成\n" if isFinal else "状态: 阅卷中, 可能有部分考生成绩未录入\n"
    string += "科目: "
    string += ", ".join(subjectList)
    string = string + "\n"
    string += "班级: "
    string += ", ".join(classList)
    string = string + "\n"
    return string, subjectList, classList


# 根据 examID 和 考生准考证号 获取学生成绩.
def getStudentScore(account, examID, studentName = "", subjectID = "", classID = "", start = None, end = None, translate = False, showProgress = False):
    if not subjectID: # 在智学网中, 获取成绩排序时需传入排序依据科目和排名范围
        subjectID = "score" # 如果调用函数时没有输入范围, 则默认按总分排序.
    # 7. 获取排名第一页的数据. 可以看到order就是排序依据科目的id (总分的id是 'score' ), classId则是排序范围 (每个班级都有随机id, 在之前的函数中已经根据班级名称获取到了id. ) 如果排序范围不填, 就是在全部参考的学生中排序.
    result = getData(account, "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank?examId=%s&searchValue=%s&pageIndexInt=1&direction=DESC&order=%s&classId=%s" % (examID, studentName, subjectID, classID))
    if translate:
        # 如果paperInfo在结果里, 说明结果不止一页 (智学网默认一页的范围是60名学生)
        # 为了便于理解, 此时我会发两张成绩数据在智学网网页上的图片给你
        if "paperInfo" in result["result"]:
            pageNum = result["result"]["paperInfo"]["totalPage"] # 获取总共页数
            pageSize = result["result"]["paperInfo"]["pageSize"] # 获取每页的结果条数 (其实这里可以不用获取, 直接设置为60就行了, 不过.. 如果智学网之后突然改了每页的条数, 就会出错. 所以最好还是从智学网获取下来这个数量)
            studentRankNum = result["result"]["paperInfo"]["totalCount"]
        else: # 如果paperInfo不在结果里, 说明只有一页
            pageNum = 1
            pageSize = 10000
            studentRankNum = len(result["result"]["studentRank"])
        
        # 这里再次获取了考试状态和科目之类的信息.
        examData = getExamDataByID(account, examID)["result"]
        examName = examData["examInfo"]["examName"]
        gradeName = examData["examInfo"]["gradeName"]
        classList = examData["classList"]
        isFinal = examData["isFinal"]
        subjectList = examData["allSubjectTopicSetList"]
        if isFinal: # 如果考试阅卷完成了, 就获取总分
            fullScore = examData["schoolExamArchive"]["standardScore"]
        studentTakedNum = examData["schoolExamArchive"]["submitStudentCount"] # 考生数量
        # 这里是准备返回的结果, 接下来就是循环获取每一页, 并且把结果简化, 丢去不要用的信息
        resultTranslated = {"subjectList": subjectList, "classList": classList, "examName": examName, "isFinal": isFinal,"studentTakedNum": studentTakedNum, "studentRankNum": studentRankNum, "studentList": []}
        # 忘记说了, start和end是要获取的排名的范围, 因为QQ机器人也显示不下全部的学生.
        # 如果只要获取第65~70名, 就完全没必要先全部获取再取出这部分了, 特别费时间, 还有可能被智学网风控 大概明白了，我先看看代码 ok
        if (start and end):
            # 这里是计算要获取的页数的范围. 用要获取的名次-1后除以每页结果数再加1
            startPage = (start-1)//pageSize + 1
            endPage = (end-1)//pageSize + 1
        
        # 8. 接下来就开始循环获取并简化结果了.
        for page in range(1, pageNum+1):
            if showProgress: print("\r[%d/%d] 正在获取成绩." % (page, pageNum), end = "")
            if (start and end): # 如果要获取的页数不在有用的范围内, 就直接跳过.
                if page < startPage:

                    continue
                if page > endPage:
                    continue
            if page != 1: # 如果页数为1, 就也跳过. 可以看到第231行已经获取了第一页的结果.
                result = getData(account, "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank?examId=%s&searchValue=%s&pageIndexInt=%d&direction=DESC&order=%s&classId=%s" % (examID, studentName, page, subjectID, classID))
            studentIndex = (page-1)*pageSize
            studentList = result["result"]["studentRank"]
            # 遍历每一位学生.
            for student in studentList:
                studentIndex += 1
                if (start and end): # 如果学生的名次不在要获取的名次内, 就不返回他的数据了.
                    if studentIndex < start:
                        continue
                    if studentIndex > end:
                        continue
                if isFinal: # 如果阅卷结束了, 就把总分, 总排名之类的信息加上.
                    data = {
                        "studentName": student["userName"],
                        "className": student["className"],
                        "studentIndex": studentIndex,
                        "score": {
                            "总分": {
                                "分数": student["allScore"],
                                "满分": str(int(float(fullScore))),
                                "校排名": student["schoolRank"],
                                "班排名": student["classRank"]
                            }
                        }
                    }
                else: # 如果没有结束, 这些信息也不能获取到, (不然会直接报错), 所以就返回 "-" 代表没有信息.
                    data = {
                        "studentName": student["userName"],
                        "className": student["className"],
                        "studentIndex": studentIndex,
                        "score": {
                            "总分": {
                                "分数": "-",
                                "满分": "-",
                                "校排名": "-",
                                "班排名": "-"
                            }
                        }
                    }
                # 然后遍历每一科分数, 将学科代码转换为学科名称.
                # 我 print 一下原始数据
                # 终端往上翻一点, 应该能看到字典数据
                # 其中subjectCode代表了科目, score是分数.
                # 那.. 怎么把subjectCode转换为文字呢..? 之前获取了subjectList的科目信息. (250行), 这里输出看看
                # 是这样的字典: [{'sort': 0, 'subjectName': '总分', 'subjectCode': '00', 'subjectGroupFlag': '0', 'standScore': 760.0}, {'subjectName': '语文', 'sort': 1, 'topicSetId': 'e8a92acf-2cd5-4269-8f58-349c4460e38a', 'subjectCode': '01', 'standScore': 120.0}, {'subjectName': '数学', 'sort': 2, 'topicSetId': '6b4a0bb8-bd0f-48f1-a792-b67819a1ff13', 'subjectCode': '02', 'standScore': 120.0}, {'subjectName': '英语', 'sort': 3, 'topicSetId': '22c1a15d-9de7-446d-96e0-bc44a9c2d0c1', 'subjectCode': '03', 'standScore': 120.0}, {'subjectName': '文综', 'sort': 10, 'topicSetId': 'aed26533-37f0-4fcc-ae62-8f14a0a16c9a', 'subjectCode': '114', 'standScore': 200.0}, {'subjectName': '理综', 'sort': 10, 'topicSetId': 'ac9ccd0b-7a2b-4b7e-a66e-d9f0e2950bfe', 'subjectCode': '115', 'standScore': 200.0}, {'subjectName': '物理', 'topicSetId': 'ac9ccd0b-7a2b-4b7e-a66e-d9f0e2950bfe!05', 'subjectCode': '05', 'standScore': '100.0', 'statStudentCount': '331'}, {'subjectName': '化学', 'topicSetId': 'ac9ccd0b-7a2b-4b7e-a66e-d9f0e2950bfe!06', 'subjectCode': '06', 'standScore': '100.0', 'statStudentCount': '331'}, {'subjectName': '政治', 'topicSetId': 'aed26533-37f0-4fcc-ae62-8f14a0a16c9a!27', 'subjectCode': '27', 'standScore': '100.0', 'statStudentCount': '331'}, {'subjectName': '历史', 'topicSetId': 'aed26533-37f0-4fcc-ae62-8f14a0a16c9a!12', 'subjectCode': '12', 'standScore': '100.0', 'statStudentCount': '331'}]
                # 可以看到, 每个sunjectCode都在这里有信息, 比如对应的学科名称, 这一科的满分分数之类的.
                for subject in student["scoreInfos"]:
                    subjectName = ""
                    for subjectData in subjectList:
                        if subject["subjectCode"] == subjectData["subjectCode"]: # 所以遍历学科列表, 如果他们的subjectCode相等了, 就能把学科code转换成学科名字.
                            subjectName = subjectData["subjectName"]
                            subjectFullScore = subjectData["standScore"]
                            break
                    if not subjectName: raise Exception("无法获取科目码和科目名称的关系.") # 找不到就只能报错了
                    # 刚刚的分数信息是这样的: {'adrkRank': '-', 'assignScore': '0', 'classCompareRank': '2', 'classRank': '3', 'isBalance': False, 'schoolCompareRank': '3', 'schoolRank': '22', 'score': '105', 'subjectCode': '01', 'subjectLevel': 1, 'tScore': '61.16'}
                    # 在这里, subjectCode: 01 目前表示语文. 然后score就是分数.
                    subjectScore = subject["score"]
                    subjectSchoolRank = subject["schoolRank"]
                    subjectClassRank = subject["classRank"]
                    data["score"].update({
                        subjectName: {
                            "分数": subjectScore,
                            "满分": str(int(float(subjectFullScore))),
                            "校排名": subjectSchoolRank,
                            "班排名": subjectClassRank
                        }
                    }) # 信息加入列表中.
                resultTranslated["studentList"].append(data)
            if not studentList:
                raise Exception("未查询到结果.")
    return resultTranslated # 然后返回排名信息.


# 根据 examID 和 考生准考证号 获取一名学生的考试成绩并转换成文字.
def getStudentStrScore(account, examID, studentName = "", subjectID = "", classID = ""):
    result = getStudentScore(account, examID, studentName, subjectID, classID, translate = True)
    studentList = result["studentList"] # 这里是学生成绩结果
    subjectList = result["subjectList"] # 这里是科目列表
    studentTakedNum = result["studentTakedNum"] # 参考人数
    isFinal = result["isFinal"] # 是否完成
    examName = result["examName"] # 考试名称
    string = examName + "\n"
    if len(studentList) >= 2: # 查到2人以上, 提示重新查询.
        raise Exception("查到 %s 位学生, 无法处理." % len(studentList))
    elif len(studentList) == 0: # 未查询到, 提示检查考号或名字.
        raise Exception("未查询到结果.")
    studentName = studentList[0]["studentName"] # 这是学生名字.
    className = studentList[0]["className"] # 学生所在班级

    # 到这里数据都获取好了, 接下来的部分是根据字典的数据, 生成文本信息.
    if not isFinal:
        string += "此考试阅卷未完成, 可能有部分考生成绩未录入\n"
    string += ("考生姓名: %s\n" % studentName)
    string += ("所在班级: %s\n" % className)
    string += ("考试成绩: (参考人数: %s)\n" % studentTakedNum)# 已经是一头雾水了qaq  我尽量说明
    scoreList = studentList[0]["score"] # 取出学生各科分数信息.
    for subject in scoreList: # 将考生每一科目的成绩转成文字信息.
        string += ("%s. %s/%s, 年级排名: %s, 班级排名: %s\n" % (subject, scoreList[subject]["分数"], scoreList[subject]["满分"], scoreList[subject]["校排名"], scoreList[subject]["班排名"]))
    return string
    # 这边可能好了, 然后到QQ机器人那边接上这个.嗯
        

# 根据 examID 和 班级名称 和 学科名称 获取排名.
def getStudentRank(account, examID, subjectName = None, className = None, start = None, end = None, showProgress = False):
    examData = getExamDataByID(account, examID)["result"] # 获取考试信息. 3. 要获取排名, 首先要先获取考试信息 (里面包含班级和科目列表)

    # 4. 考试信息获取到之后, 根据智学网的格式取出信息就可以了 (Python字典的用法相信你肯定了解过)
    isFinal = examData["isFinal"] # 是否阅卷完成.
    classList = examData["classList"] # 班级列表.
    subjectList = examData["allSubjectTopicSetList"] # 科目列表.
    if isFinal:
        for subject in subjectList:
            if subject["subjectName"] == "总分":
                subject["topicSetId"] = ""
    classList.append({
        "name": "全部",
        "id": ""
    })

    # 5. 获取排名前, 先要检测排名范围(className)和排序方式(subjectName)是否在考试信息里, 不然就获取不到.
    # 检测学科是否存在.
    if subjectName is None:
        subjectName = "总分"
    subjectID = "未找到"
    for subject in subjectList:
        if subjectName == subject["subjectName"]:
            subjectID = subject["topicSetId"]
            break
    if subjectID == "未找到":
        errmsg = "学科未找到. (学科列表: "
        errmsg += (", ".join([subject["subjectName"] for subject in subjectList]))
        errmsg += ")"
        raise ValueError(errmsg)

    # 检测班级名称是否存在.
    if className is None:
        className = "全部"
    classID = "未找到"
    for class_ in classList:
        if className == class_["name"]:
            classID = class_["id"]
            break
    if classID == "未找到":
        errmsg = "班级未找到. (班级列表: "
        errmsg += (", ".join([class_["name"] for class_ in classList]))
        errmsg += ")"
        raise ValueError(errmsg)

    # 获取数据.
    result = getStudentScore(account, examID, "", subjectID, classID, start, end, translate = True, showProgress = showProgress) # 6. 检验通过后, 再通过这个函数获取分数信息. (重点在这)
    if not result["studentList"]:
        raise Exception("未查询到结果.")
    # 信息获取到了, 接着和考试信息一起返回给把字典信息转文字的函数
    return {"examData": examData, "rank": result}


# 根据 examID 和 班级名称 和 学科名称 获取排名并转换成文字.  hi 这里是生成排名文字信息的, 下方的终端能看到吗..? 能
# 我讲解一下获取过程..? 嗯
def getStudentStrRank(account, examID, subjectName = None, className = None, start = None, end = None, showProgress = False):
    result = getStudentRank(account, examID, subjectName, className, start, end, showProgress) # 2. 然后使用这个函数获取字典格式的信息. 接下来看看这个函数是怎样获取信息的.
    # 可以看看信息格式是怎样的
    # print(json.dumps(result["rank"], ensure_ascii = False, indent = 4)) # 这是将字典输出得更好看的方法. (ensure_ascii = False表示保留中文字符, indent表示缩进格式) ...控制台好像显示不下了, 少输出一点看看. 
    # 信息是这样的, 首先是科目信息. 然后也有班级信息 有考试名称
    # 最重要的就是按排名出现的学生成绩了. 可以看到学生每一科分数都有
    
    examData = result["examData"]
    studentList = result["rank"]["studentList"]
    string = ""
    isFinal = examData["isFinal"] # 是否阅卷完成.
    examName = examData["examInfo"]["examName"] # 考试名称. 
    gradeName = examData["examInfo"]["gradeName"] # 年级名称.
    schoolName = examData["examInfo"]["schoolName"] # 学校名称.
    updateTime = examData["schoolExamArchive"]["createDateTime"] # 更新时间.
    updateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updateTime/1000)) # 将时间戳转化为正常的时间格式.
    studentTakedNum = examData["schoolExamArchive"]["submitStudentCount"] # 参考人数.
    studentRankNum = result["rank"]["studentRankNum"] # 范围内排名人数.
    classList = examData["classList"] # 班级列表.
    subjectList = examData["allSubjectTopicSetList"] # 科目列表.

    # 设置初始信息.
    if subjectName is None:
        subjectName = "总分"
    if className is None:
        className = "全部"
    if start is None:
        start = 1

    string += "状态: 已完成\n" if isFinal else "状态: 阅卷中, 可能有部分考生成绩未录入\n"
    string += ("参考人数: %s\n" % studentTakedNum)
    string += ("此范围内排名人数: %s\n" % studentRankNum)
    string += ("%s 学生在 %s 考试中按 %s 排序如下:\n" % (className, examName, subjectName))
    for index, student in enumerate(studentList):
        if start+index != student["studentIndex"]:
            raise Exception("排名数据核对错误.")
        # 最后在这里拼接上排名数据就行了. 因为我技术水平还不高, 所以还没找到同分情况下将排名设为相同的方法
        if className == "全部":
            string += ("%s. %s %s, %s\n" % (student["studentIndex"], student["className"], student["studentName"], student["score"][subjectName]["分数"]))
        else:
            string += ("%s. %s, %s\n" % (student["studentIndex"], student["studentName"], student["score"][subjectName]["分数"]))
    return string


if __name__ == "__main__":
    print(getExamListStrByYear("明德麓谷学校", year = 2019, page = 1)) # 获取明德麓谷学校2019级的考试列表.
    print("\n")
    print(getExamListStrByGrade("明德麓谷学校", grade = "初三", page = 1)) # 获取明德麓谷学校初三的考试列表.
    print("\n")
    print(getExamDataStrByID("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165")[0]) # 获取 初三全真模拟(明德麓谷学校2019级) 考试详情. (此考试是2019级在校的最后一场考试)
    print(getStudentStrScore("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165", studentName = "99427569")) # 获取准考证号为 99427569 的学生在 初三全真模拟(明德麓谷学校2019级) 的考试成绩.

    # 使用函数的方法在这里, 可以看到传入了排名排序的范围(className)和排序的方式(subjectName)
    # 所以这里运行, 就可以显示排名了. 能检测到同分的有多少人吗
    # 有些难... 还有一个问题, 比如说我想获取1~10名, 如果刚好有很多人都在第10名, 那是反不返回这些数据呢..? 如果不返回, 并列10名就不全. 如果返回, 可能信息长度就和程序设计者预期要处理的信息条数不同了. 
    # 所以就只能放弃并列的情况了.
    if False:
        print(getStudentStrRank("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165")) # 获取 初三全真模拟(明德麓谷学校2019级) 的考试成绩 全部学生排名. (数据很多, 可能耗时很长, 有300多学生)
    print(getStudentStrRank("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165", subjectName = "总分", className = "九年级1907", start = 2, end = 10)) # 获取 九年级1907班范围内 初三全真模拟(明德麓谷学校2019级) 的考试成绩第2~10名.
    print(getStudentStrRank("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165", subjectName = "数学", className = "九年级1907", start = 10, end = 15)) # 获取 九年级1907班范围内 按数学排序 初三全真模拟(明德麓谷学校2019级) 的考试成绩第10~15名.
    input() # 最后控制台的效果应该还算可以 那.. 就接上QQ机器人试试..? 嗯
    # 8797fe68-2375-4872-b6a8-5a4f6c729634

    # https://www.zhixue.com/api-union/customized/downloadTask/userAchievementMarkingExport?&examId=65bb218d-dea5-4d10-b560-ce64d7f34dd1

    # https://www.zhixue.com/api-teacher/api/president/getExcelDownLoadTaskInfo?examId=2be5e24a-512d-4593-b8b9-c532553e0937&lastExamId=30e59c28-7282-4049-9485-efa1fc2abfc9&fileType=school_score_student&type=normal&version=V3&t=1660664227557
    # https://www.zhixue.com/api-teacher/api/president/getExcelDownLoadTaskInfo?examId=91b4249a-8150-4909-b929-d82819ba9d9f&fileType=school_score_student&type=normal&version=V3&t=1660664227557

    # https://www.zhixue.com/api-teacher/class/downloadFile?url=oss_/7b4bfeb8-2b02-49b5-af61-6a0e46cee2a8_20220816.zip&fileName=

    # https://www.zhixue.com/api-teacher/api/president/getExcelDownLoadTaskInfo?examId=65bb218d-dea5-4d10-b560-ce64d7f34dd2&fileType=school_score_student&type=normal&version=V3

    # https://www.zhixue.com/api-union/customized/downloadTask/userAchievementMarkingExport?&examId=65bb218d-dea5-4d10-b560-ce64d7f34dd1

    # https://www.zhixue.com/webexam/mmG3xH0zd/#/markingtools/markingtools/main/?hideCommonHead=true&hideCommonFoot=true&examId=de74c714-6cc9-4d50-ba5c-03971d5f9bc3

    # https://www.zhixue.com/htm-freshreport/#/singleExamSetting/dealReport?schoolId=2300000001000049726&examId=0c116fc3-117c-462c-95be-a5db13ca7165&hideCommonHead=true