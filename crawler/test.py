nums = [2, 7, 11, 15]
target = 9

def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range (i + 1, len(nums)): 
            if nums[i] + nums[j] == target: 
                return [i, j]
    return []


def two_sum_fast(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

result = two_sum(nums, target)
print(result) 





     
     
     