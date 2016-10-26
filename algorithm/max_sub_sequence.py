#!/usr/bin/env python
# encoding: utf-8


def max_sub_sequence_sum(sequence):
    """最大子序列求和
    """
    maxsum, prevsum = 0, 0
    start, end = 0, 0
    for i, v in enumerate(sequence):
        prevsum += v
        if prevsum > maxsum:
            maxsum = prevsum
            end = i
        elif prevsum < 0:
            prevsum = 0
            start = i

    return maxsum, start, end


def test():
    print(max_sub_sequence_sum([1, 3, -1, -2]))


if __name__ == "__main__":
    test()
