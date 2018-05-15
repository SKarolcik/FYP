/*
 * Linux Kernel module using GPIO interrupts.
 *
 * Author:
 * 	Interrupt handling part - Stefan Wendler (devnull@kaltpost.de)
 *  Device part :
 *     Copyright (C) 2013, Jack Whitham
 *     Copyright (C) 2009-2010, University of York
 *     Copyright (C) 2004-2006, Advanced Micro Devices, Inc.
 *
 *  Modified by Stefan Karolcik for the use with parallalel 12-bit ADC and Raspberry Pi to achieve real-time data acquisition.
 *
 * This software is licensed under the terms of the GNU General Public
 * License version 2, as published by the Free Software Foundation, and
 * may be copied, distributed, and modified under those terms.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 */
#include <linux/device.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>
#include <linux/time.h>
#include <linux/fs.h>
#include <linux/uaccess.h>

#define GPIO_FOR_RX_SIGNAL	17
#define GPIO_BIT0_ADC		18
#define GPIO_BIT1_ADC		19
#define GPIO_BIT2_ADC		20
#define GPIO_BIT3_ADC		21
#define GPIO_BIT4_ADC		22
#define GPIO_BIT5_ADC		23	
#define GPIO_BIT6_ADC		24
#define GPIO_BIT7_ADC		25
#define GPIO_BIT8_ADC		26
#define GPIO_BIT9_ADC		27
#define GPIO_BIT10_ADC		5
#define GPIO_BIT11_ADC		6

#define DEV_NAME 			"adccomms" 
#define BUFFER_SZ			1048576 

#define BCM2708_PERI_BASE       0x3F000000
#define GPIO_BASE               (BCM2708_PERI_BASE + 0x200000)	// GPIO controller  


static uint32_t pxValue[BUFFER_SZ];  //Buffer with ADC values
static int  pRead;					 //Ring buffer control signals
static int  pWrite;
static int  wasOverflow;
static int  prevPx;					//Value of previous sample, to store 2 samples per buffer entry

volatile uint32_t *gpio_reg;

/* Later on, the assigned IRQ numbers for the buttons are stored here */
static int rx_irqs[] = { -1 };

/*
 * The interrupt service routine called on every pin status change
 */
static irqreturn_t rx_isr(int irq, void *data)
{

   	uint32_t curPx = 0;

	curPx = *(gpio_rd.addr + 13);
	curPx = (curPx & (0b1111111111<<(18)))>>(18) + (curPx & (0b11<<(5)))<<(5);
	/*
	if (prevPx == 0){
		prevPx = curPx;
	}else{
		curPx = (curPx << (16)) + prevPx;
		prevPx = 0;
		pxValue[pWrite] = curPx;
		pWrite = (pWrite + 1)  & (BUFFER_SZ - 1);
	} 
	*/
	pxValue[pWrite] = curPx;
	pWrite = (pWrite + 1)  & (BUFFER_SZ - 1);
	
	if (pWrite == pRead) {
		// overflow
		pRead = ( pRead + 1 ) & (BUFFER_SZ-1);
		if ( wasOverflow == 0 ) {
	       printk(KERN_ERR "EXT_ADC - Buffer Overflow - IRQ will be missed");
	       wasOverflow = 1;
	    }
	} else {
		wasOverflow = 0;
	}
	return IRQ_HANDLED;
}


static int ext_adc_open(struct inode *inode, struct file *file)
{
    return nonseekable_open(inode, file);
}

static int ext_adc_release(struct inode *inode, struct file *file)
{
    return 0;
}

static ssize_t ext_adc_write(struct file *file, const char __user *buf,
                size_t count, loff_t *pos)
{
	return -EINVAL;
}

static ssize_t ext_adc_read(struct file *file, char __user *buf,
                size_t count, loff_t *pos)
{
	// returns one of the line with the time between two IRQs
	// return 0 : end of reading
	// return >0 : size
	// return -EFAULT : error
	char tmp[256];
	int _count;
	int _error_count;

	_count = 0;
	if ( pRead != pWrite ) {
		sprintf(tmp,"%d\n",pxValue[pRead]);
  	    _count = strlen(tmp);
        _error_count = copy_to_user(buf,tmp,_count+1);
        if ( _error_count != 0 ) {
        	printk(KERN_ERR "EXT_ADC - Error writing to char device");
            return -EFAULT;
        }
		pRead = (pRead + 1) & (BUFFER_SZ-1);
	}
	return _count;
}

static struct file_operations ext_adc_fops = {
    .owner = THIS_MODULE,
    .open = ext_adc_open,
    .read = ext_adc_read,
    .write = ext_adc_write,
    .release = ext_adc_release,
};

static struct miscdevice ext_adc_misc_device = {
    .minor = MISC_DYNAMIC_MINOR,
    .name = DEV_NAME,
    .fops = &ext_adc_fops,
};



/*
 * Module init function
 */
static int __init adccomms_init(void)
{
	int ret = 0;
	printk(KERN_INFO "%s\n", __func__);

	// INITIALIZE IRQ TIME AND Queue Management
	//getnstimeofday(&lastIrq_time);
	pRead = 0;
	pWrite = 0;
	wasOverflow = 0;
	prevPx = 0;

	gpio_reg = (uint32_t *)ioremap(GPIO_BASE, 41*4);
	if (gpio_reg != NULL){
		printk(KERN_INFO "Succesfully mapped GPIO port"); 
	}

	// register GPIO PIN in use
	ret = gpio_request_array(signals, ARRAY_SIZE(signals));

	if (ret) {
		printk(KERN_ERR "EXT_ADC - Unable to request GPIOs for RX Signals: %d\n", ret);
		goto fail2;
	}
	
	// Register IRQ for this GPIO
	ret = gpio_to_irq(signals[0].gpio);
	if(ret < 0) {
		printk(KERN_ERR "EXT_ADC - Unable to request IRQ: %d\n", ret);
		goto fail2;
	}
	rx_irqs[0] = ret;
	printk(KERN_INFO "EXT_ADC - Successfully requested RX IRQ # %d\n", rx_irqs[0]);
	ret = request_irq(rx_irqs[0], rx_isr, IRQF_TRIGGER_FALLING | 0, "extadc#rx", NULL);
	if(ret) {
		printk(KERN_ERR "EXT_ADC - Unable to request IRQ: %d\n", ret);
		goto fail3;
	}

	// Register a character device for communication with user space
    misc_register(&ext_adc_misc_device);

	return 0;

	// cleanup what has been setup so far
fail3:
	free_irq(rx_irqs[0], NULL);

fail2: 
	gpio_free_array(signals, ARRAY_SIZE(signals));
	return ret;	
}

/**
 * Module exit function
 */
static void __exit adccomms_exit(void)
{
	printk(KERN_INFO "%s\n", __func__);

    misc_deregister(&ext_adc_misc_device);
	iounmap(gpio_reg); //unmap the gpio reg address
	
	// free irqs
	free_irq(rx_irqs[0], NULL);	
	
	// unregister
	gpio_free_array(signals, ARRAY_SIZE(signals));
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Stefan Karolcik");
MODULE_DESCRIPTION("Linux Kernel Module for fast communication with parallel 12-bit ADC");

module_init(adccomms_init);
module_exit(adccomms_exit);