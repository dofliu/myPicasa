#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
執行所有單元測試的腳本
使用方式: python run_tests.py
"""
import unittest
import sys
import os

# 將專案根目錄加入路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_tests():
    """執行所有測試"""
    # 建立測試套件
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')

    # 執行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 回傳測試結果
    return result.wasSuccessful()


if __name__ == '__main__':
    # 執行測試
    success = run_all_tests()

    # 根據測試結果設定退出碼
    sys.exit(0 if success else 1)
