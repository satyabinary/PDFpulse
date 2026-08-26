# # key = int(input("Enter key to search: "))
# # arr = [1, 3, 5, 7, 8, 9]

# # start = 0
# # end = len(arr) - 1
# # found = False

# # while start <= end:

# #     mid = (start + end) // 2
    
    
# #     if arr[mid] == key:
# #         print("Key found at index:", mid)
# #         found = True
# #         break
    
# #     elif arr[mid] < key:
# #         start = mid + 1
# #     else:
# #         end = mid - 1

# # if not found:
# #     print("Key not found in the array")

# # arr = [1, 2, 3, 4]

# # prefix = []
# # sum = 0

# # for x in arr:
# #     sum += x
# #     prefix.append(sum)

# # print(prefix)

# arr = [2, 4, 6, 8, 10]

# l = 1
# r = 3

# sum = 0

# for i in range(l, r + 1):
#     sum += arr[i]

# print(sum)
arr = [2, 4, 6, 8, 10]

prefix = [0] * len(arr)
prefix[0] = arr[0]

for i in range(1, len(arr)):
    prefix[i] = prefix[i - 1] + arr[i]

queries = [(1, 3), (0, 2), (2, 4)]

for l, r in queries:

    if l == 0:
        ans = prefix[r]
    else:
        ans = prefix[r] - prefix[l - 1]

    print(ans)