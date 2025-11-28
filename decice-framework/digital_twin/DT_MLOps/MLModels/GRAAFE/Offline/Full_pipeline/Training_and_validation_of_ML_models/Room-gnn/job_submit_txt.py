import os

arr = os.listdir('samples_batch_files/')
print(len(arr))
s = ''
for i in arr:
    s = s + 'sbatch {};'.format(i)
print(s)