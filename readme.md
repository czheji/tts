# 微软tts python版demo(cli)

来自： https://github.com/skygongque/tts
## 使用方法

安装依赖

```shell
pip install -r requirements.txt
```

运行

```shell
python pkg/tts.py --input ./examples/demo.txt
```

> 使用`python` 运行`tts.py`，通过参数`input`传入文本文件的路径
> 默认使用同目录下的 `config.yml`配置文件，可以通过`config`参数更改
> 或者可以通过传入`output` 传入希望保存的文件名

```shell
python pkg/tts.py --input ./examples/demo.txt --config ./examples/config.yml --output demo.mp3
```

带有自定义标签的文本文件的示例如下

```txt
【男1】你好，这里是男1的语音。
【女1】你好，这里是女1的语音。
由于没有标签，这行使用默认语音朗读。
这里还是默认语音。
【不存在】没有找到配置，使用默认语音。
【男1】<phoneme alphabet="sapi" ph="zhong 4 zhong 4">重重</phoneme>和重重，读的对吗？
【女1:angry】能听出我很生气吗，这里还是女1。
【男1:,Boy】这里还是男1，不过我现在的角色是男孩。
【男1:,Girl】这里还是男1，我现在的角色是女孩<break strength="strong" />不过，我不会扮演这个角色啊，还是回到了我原来的声音。
【女1:,Boy】这里还是女1，我现在的角色也是男孩。
【女1】标签必须在每行的开始位置，并且每行只有一个生效，【男1】这个是不起作用的。
```

> `【男1】` 标签，在config.yml中配置的一个tag 

> `config.yml`示例如下

```yml
out_bitrate: 64k
out_format: opus # mp3 aac opus
format: audio-24khz-160kbitrate-mono-mp3 # riff-24khz-16bit-mono-pcm audio-24khz-160kbitrate-mono-mp3
templates:
  - tag: 女1
    name: zh-CN-XiaomoNeural
  - tag: g
    name: zh-CN-XiaomoNeural
    style: gentle
    role: YoungAdultMale
  - tag: 男1
    name: zh-CN-YunxiNeural
    role: Narrator
    style: narration-relaxed
default: g
limit:
  word_count: 300 #字数限制，若转换报错请减小这个值
  ssml_count: 700 #SSML字数限制，若转换报错请减小这个值
```

## 使用SSML

> 文本中可以包含SSML标签，所以可以直接使用SSML来改变发音、设置停顿或某些文本静音，这些的文档和示例可以在微软的文档中找到：
> [通过SSML改进合成-停顿](https://learn.microsoft.com/zh-cn/azure/cognitive-services/speech-service/speech-synthesis-markup?tabs=csharp#add-or-remove-a-break-or-pause) 
> [SSML中使用拼音改变字词的发音](https://learn.microsoft.com/zh-cn/azure/cognitive-services/speech-service/speech-ssml-phonetic-sets#zh-cn)

### 常用声音和风格列表

注'General'不用添加到sytle中

|           中文名           | voice name             | 支持风格 style                                               |
| :------------------------: | ---------------------- | ------------------------------------------------------------ |
|  Xiaoxiao (Neural) - 晓晓  | zh-CN-XiaoxiaoNeural   | 'general', 'assistant', 'chat', 'customerservice', 'newscast', 'affectionate', 'angry', 'calm', 'cheerful', 'disgruntled', 'fearful', 'gentle', 'lyrical', 'sad', 'serious' |
|  Yunyang (Neural) - 云扬   | zh-CN-YunyangNeural    | 'general', 'customerservice', 'narration-professional', 'newscast-casual' |
|  Xiaochen (Neural) - 晓辰  | zh-CN-XiaochenNeural   | 'general'                                                    |
|  Xiaohan (Neural) - 晓涵   | zh-CN-XiaohanNeural    | 'general', 'calm', 'fearful', 'cheerful', 'disgruntled', 'serious', 'angry', 'sad', 'gentle', 'affectionate', 'embarrassed' |
|   Xiaomo (Neural) - 晓墨   | zh-CN-XiaomoNeural     | 'general', 'embarrassed', 'calm', 'fearful', 'cheerful', 'disgruntled', 'serious', 'angry', 'sad', 'depressed', 'affectionate', 'gentle', 'envious' |
|  Xiaoqiu (Neural) - 晓秋   | zh-CN-XiaoruiNeural    | 'general'                                                    |
|  Xiaorui (Neural) - 晓睿   | zh-CN-XiaoruiNeural    | 'general', 'calm', 'fearful', 'angry', 'sad'                 |
| Xiaoshuang (Neural) - 晓双 | zh-CN-XiaoshuangNeural | 'general', 'chat'                                            |
|  Xiaoxuan (Neural) - 晓萱  | zh-CN-XiaoxuanNeural   | 'general', 'calm', 'fearful', 'cheerful', 'disgruntled', 'serious', 'angry', 'gentle', 'depressed' |
|  Xiaoyan (Neural) - 晓颜   | zh-CN-XiaoyanNeural    | 'general'                                                    |
|  Xiaoyou (Neural) - 晓悠   | zh-CN-XiaoyouNeural    | 'general'                                                    |
|   Yunxi (Neural) - 云希    | zh-CN-YunxiNeural      | 'general', 'narration-relaxed', 'embarrassed', 'fearful', 'cheerful', 'disgruntled', 'serious', 'angry', 'sad', 'depressed', 'chat', 'assistant', 'newscast' |
|   Yunye (Neural) - 云野    | zh-CN-YunyeNeural      | 'general', 'embarrassed', 'calm', 'fearful', 'cheerful', 'disgruntled', 'serious', 'angry', 'sad' |

以上是中文部分的，微软的tts支持100多种语音，其他的语音自己在网页上查看吧

以下是微软的相关网站：

[声音、风格和角色](https://learn.microsoft.com/zh-cn/azure/cognitive-services/speech-service/language-support?tabs=stt-tts#voice-styles-and-roles)

[微软的网页示例，可以参考SSML](https://azure.microsoft.com/zh-cn/products/cognitive-services/text-to-speech/#features)
