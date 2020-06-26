# Given 90 minutes, I was tasked with writing a function: solution(N, artifacts, searched)
# This function was given:
#           N: Number given to specify size of a NxN square map grid
#           artifacts: string of comma separated pairs of coordinates of buried treasure (e.g. 'A1 B2, C3 C3' means A1, A2, B1, B2, and C3 are all filled)
#                           (EACH PAIR CORRESPONDS TO PIECES OF A UNIQUE TREASURE)
#           searched: string of coordinates that have been searched (e.g. 'A1 A2 A3 A4')
# The goal of this function is to return [x, y] where:
#           x: number of complete sets of treasure found
#           y: number of incomplete sets of treasure found
# What I have written met that goal in ~85 minutes. It may or may not fail some edge cases I haven't considered.

def solution(N, artifacts, searched):
    # ord('A') returns 65, so we subtract 64 from each letter to find it's column index (starting from 1)
    numComplete = numIncomplete = 0

    myMap = [[' ' for x in range(N)] for y in range(N)]

    if ',' in artifacts:
        locPairList = artifacts.split(',')
    elif artifacts != '':
        locPairList = [artifacts]

    counter = 1
    for pair in locPairList:
        left, right = pair.split(' ')[0], pair.split(' ')[1]
        if len(left) == 2:
            leftNum = int(left[0])
            leftLetter = left[1]
        elif len(left) == 3:
            leftNum = int(str(left[0]) + str(left[1]))
            leftLetter = left[2]
        if len(right) == 2:
            rightNum = int(right[0])
            rightLetter = right[1]
        elif len(right) == 3:
            rightNum = int(str(right[0]) + str(right[1]))
            rightLetter = right[2]

        rowVal = leftNum
        while rowVal <= rightNum:
            colVal = ord(leftLetter)
            while colVal <= ord(rightLetter):
                myMap[rowVal-1][colVal - 65] = counter
                colVal += 1
            rowVal += 1
        counter += 1

    numSet = set()
    if searched != '':
        searchList = searched.split(' ')
        for location in searchList:
            if len(location) == 2:
                num = int(location[0])
                letter = location[1]
            elif len(location) == 3:
                num = int(str(location[0]) + str(location[1]))
                letter = location[2]
            if type(myMap[num - 1][ord(letter) - 65]) == int:
                numSet.add(myMap[num - 1][ord(letter) - 65])
            myMap[num - 1][ord(letter) - 65] = 'X'

        searchCount = 1
        encountered = False
        while searchCount < counter:
            for x in myMap:
                if searchCount in x:
                    if searchCount in numSet:
                        numIncomplete += 1
                    encountered = True
                    break
            if encountered == False:
                numComplete += 1
            else:
                encountered = False
            searchCount += 1

    return [numComplete, numIncomplete]


if __name__ == "__main__":
    print(solution(4, '1B 2C,2D 4D', '2B 2D 3D 4D 4A'))
    print(solution(3, '1A 1B,2C 2C', '1B'))
    print(solution(12, '1A 2A,12A 12A', '12A'))