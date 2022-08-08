import requests, typing, json, urllib.parse, time



# 账号列表. (仅支持教师账号)
accountList = {
    "学校名称": {
        "account": 1234567890987654321, # 19位的纯数字账号.
        "password": "password", # 密码
        "session": requests.Session(), # 这里不用管.
        "data": {} # 这里也不用
    }
}


# 登录 accountList 中的账号, 并将会话信息存至其字典的 session 中. 
def login(account):
    if account not in accountList: # 检查账号是否在 accountList 中.
        raise Exception("账号未找到.")
    username, password, session = accountList[account]["account"], accountList[account]["password"], accountList[account]["session"] # 取出账号, 密码以及会话信息.

    # 登录第一部分, 发送登录请求.
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
    data = {
        "ticket": st,
    }
    result = session.post("https://www.zhixue.com/ssoservice.jsp", params = data).text
    result = result.split("\n", 1)[0]
    if result != "success": # 检查登录是否成功.
        raise Exception(result)


# 通过对应账号的会话进行 requests.get, 获取信息.
def getData(account, url):
    if account not in accountList:
        raise Exception("账号未找到.")
    result = accountList[account]["session"].get(url).text # 通过会话获取数据.
    if result.startswith("<!DOCTYPE html>"): # 检查是否获取到数据了.
        login(account) # 如果智学网返回的是 html 代码, 说明没有登录或会话过期或数据不存在, 所以重新尝试登录.
        result = accountList[account]["session"].get(url).text # 再次获取数据.
        if result.startswith("<!DOCTYPE html>"): # 如果智学网返回的还是 html 代码, 说明排除了没有登录或会话过期的可能, 只有可能是数据不存在.
            raise Exception("获取失败.")
    result = json.loads(result)
    if result["message"]: # 如果智学网返回信息中 message 的值不是空的, 说明获取出错, 同时 message 的值就是错误详情.
        if result["message"] == "内部错误": # 如果错误是 内部错误, 其实就是数据没找到.
            result["message"] = "数据未找到."
        raise Exception(result["message"])
    return result


# 根据级数 (入学年份) 获取考试列表.
def getExamListByYear(account, year, page = 1):
    result = getData(account, "https://www.zhixue.com/api-teacher/api/reportlist?queryType=schoolInYear&schoolInYearCode=%d&pageIndex=%d" % (year, page))
    return result


# 根据级数 (入学年份) 获取考试列表, 并将部分结果直接转换成文字.
def getExamListStrByYear(account, year, page = 1, limit = None):
    result = getExamListByYear(account, year, page)["result"]["reportList"]
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
    studentTotalNum = examData["schoolExamArchive"]["studentCount"]
    examType = examData["examType"]
    # avgScore = examData["schoolExamArchive"]["avgScore"]
    # maxScore = examData["schoolExamArchive"]["maxScore"]
    classList = examData["classList"]
    subjectList = examData["allSubjectTopicSetList"]
    # string += ("学校名称: %s\n" % schoolName)
    string += ("考试名称: %s\n" % examName)
    string += ("考试年级: %s\n" % gradeName)
    string += ("考试类型: %s\n" % examType)
    string += ("更新时间: %s\n" % updateTime)
    string += ("参考人数: %s\n" % studentTakedNum)
    string += "状态: 已完成\n" if isFinal else "状态: 阅卷中\n"
    string += "科目: "
    for subject in subjectList:
        string += ("%s, " % subject["subjectName"])
    string = string[:-2] + "\n"
    return string


# 根据 examID 和 考生准考证号 获取学生成绩.
def getStudentScore(account, examID, studentName = "", subjectID = "", classID = "", translate = False):
    result = getData(account, "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank?examId=%s&searchValue=%s&pageIndexInt=1&direction=DESC&order=%s&classId=%s" % (examID, studentName, subjectID, classID))
    if translate:
        pageNum = result["result"]["paperInfo"]["totalPage"]
        examData = getExamDataByID(account, examID)["result"]
        examName = examData["examInfo"]["examName"]
        gradeName = examData["examInfo"]["gradeName"]
        classList = examData["classList"]
        subjectList = examData["allSubjectTopicSetList"]
        fullScore = examData["schoolExamArchive"]["standardScore"]
        studentTakedNum = examData["schoolExamArchive"]["submitStudentCount"]
        resultTranslated = {"subjectList": subjectList, "studentTakedNum": studentTakedNum, "studentList": []}
        for page in range(1, pageNum+1):
            if page != 1:
                result = getData(account, "https://www.zhixue.com/api-teacher/api/studentScore/getAllSubjectStudentRank?examId=%s&searchValue=%s&pageIndexInt=%d&direction=DESC&order=%s&classId=%s" % (examID, studentName, page, subjectID, classID))
            studentList = result["result"]["studentRank"]
            for student in studentList:
                data = {
                    "studentName": student["userName"],
                    "className": student["className"],
                    "score": {
                        "总分": {
                            "分数": student["allScore"],
                            "满分": str(int(float(fullScore))),
                            "校排名": student["schoolRank"],
                            "班排名": student["classRank"]
                        }
                    }
                }
                for subject in student["scoreInfos"]:
                    subjectName = ""
                    for subjectData in subjectList:
                        if subject["subjectCode"] == subjectData["subjectCode"]:
                            subjectName = subjectData["subjectName"]
                            subjectFullScore = subjectData["standScore"]
                            break
                    if not subjectName: raise Exception("无法获取科目码和科目名称的关系.")
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
                    })
                resultTranslated["studentList"].append(data)
    return resultTranslated


# 根据 examID 和 考生准考证号 获取一名学生的考试成绩并转换成文字.
def getStudentStrScore(account, examID, studentName = "", subjectID = "", classID = ""):
    result = getStudentScore(account, examID, studentName, subjectID, classID, translate = True)
    studentList = result["studentList"] # 这里是学生成绩结果
    subjectList = result["subjectList"] # 这里是科目列表
    studentTakedNum = result["studentTakedNum"] # 参考人数
    string = ""
    if len(studentList) >= 2: # 查到2人以上, 提示重新查询.
        raise Exception("查到 %s 个结果, 无法处理." % len(studentList))
    elif len(studentList) == 0: # 未查询到, 提示检查考号或名字.
        raise Exception("未查询到结果.")
    studentName = studentList[0]["studentName"] # 这是学生名字.
    className = studentList[0]["className"] # 学生所在班级

    # 到这里数据都获取好了, 接下来的部分是根据字典的数据, 生成文本信息.
    string += ("考生姓名: %s\n" % studentName)
    string += ("所在班级: %s\n" % className)
    string += ("考试成绩: (参考人数: %s)\n" % studentTakedNum)# 已经是一头雾水了qaq  我尽量说明
    scoreList = studentList[0]["score"] # 取出学生各科分数信息.
    for subject in scoreList: # 将考生每一科目的成绩转成文字信息.
        string += ("%s. %s/%s, 年级排名: %s, 班级排名: %s\n" % (subject, scoreList[subject]["分数"], scoreList[subject]["满分"], scoreList[subject]["校排名"], scoreList[subject]["班排名"]))
    return string
    # 这边可能好了, 然后到QQ机器人那边接上这个.嗯
        



if __name__ == "__main__":
    print(getExamListStrByYear("明德麓谷学校", year = 2021, page = 1)) # 获取明德麓谷学校2021级的考试列表. (第一页)
    print("\n")
    print(getExamDataStrByID("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165")) # 获取考试详情. (此考试是 明德麓谷学校2021级的初三全真模拟, 即2021级在校的最后一场考试)
    print(getStudentStrScore("明德麓谷学校", "0c116fc3-117c-462c-95be-a5db13ca7165", studentName = "99427569")) # 获取准考证号为 99427569 的学生在 明德麓谷学校2021级初三全真模拟 的考试成绩.
    input()
